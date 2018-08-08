#!/usr/bin/env python

import math

def createRaidSubtrace(infile, ndisk, odisk, stripe):
  out = []

  blk_size = 512
  scaler = stripe / blk_size # = chunk size
  
  def calculate_raid_blk(blk_start, blk_count, time=0):
    blk_count_per_disk = [0] * ndisk
    blk_start_per_disk = [None] * ndisk

    current_blk = blk_start
    for _ in range(blk_count):
	    current_disk = (current_blk / scaler) % ndisk
	    blk_count_per_disk[current_disk] += 1
	    if blk_start_per_disk[current_disk] is None:
                    blk_start_per_disk[current_disk] = calculate_raid_offset(current_blk)
	    current_blk += 1

    return blk_start_per_disk[odisk], blk_count_per_disk[odisk]
    
  def calculate_raid_offset(offset_input):
    return ((offset_input / (scaler * int(ndisk))) * scaler) + ((offset_input % (scaler * int(ndisk))) % scaler)

  with open("in/" + infile) as f:
    for line in f:
      token = line.split(" ")
      time = token[0]
      devno = token[1]
      blkno = int(token[2].strip())
      blkcount = int(token[3].strip())
      flags = token[4]
	
      blkno, blkcount = calculate_raid_blk(blkno, blkcount, time=time)
      if blkcount != 0:
        out.append("{} {} {} {} {}".format(time, devno, blkno, blkcount, flags))
        
  return out
        
def createAllRaidFiles(infile, ndisk, stripe):

  for i in range(0,ndisk):
    out = open("out/"+infile+"-raiddisk" + str(i) + ".trace",'w')
    
    raiddisk = createRaidSubtrace(infile,ndisk,i,stripe)
    
    for traceelm in raiddisk:
      out.write(traceelm)
    
    out.close()
    
def createAllRaidList(infile, ndisk, stripe):

  out = []

  for i in range(0,ndisk):
    out.append([])
    
    raiddisk = createRaidSubtrace(infile,ndisk,i,stripe)
    
    for traceelm in raiddisk:
      out[i].append(traceelm.split(" "))
    
  return out
    


# Added by Fadhil Imam to create raid 5 tracefile [August 3, 2018]

# Function to create all raid 5 trace files
#   infile : original tracefile
#   ndisk : number of all disk for raid 5 configuration (assuming ndisk always >= 3)
#   segment_size : size of segment in each disk (chunk size), please see : https://4.bp.blogspot.com/-P_0tQLC8lIs/Ucyk5Kpc5yI/AAAAAAAAA7I/ASAMO4y91gA/s795/Storage_segment_and_stripe_size.png
def createAllRaid5Files(infile, ndisk, segment_size):
  firstline = [True] * ndisk
  outtraces = []
  for i in range (0,ndisk):
    outfile = open("out/"+infile+"-raid5disk" + str(i) + ".trace", "w")
    outtraces.append(outfile)

  blk_size = 2048 # or sector size in hdd (in bytes)
  blk_per_segment = segment_size / blk_size
  blk_per_stripe = blk_per_segment * ndisk

  intrace = open("in/" + infile, "r")
  for line in intrace:
    token = line.split()
    time = long(token[0])
    devno = token[1]
    blkno = int(token[2])
    blkcount = int(token[3])
    operation = int(token[4])

    # calculating new starting blkno
    target_stripe_id = blkno / (blk_per_segment * (ndisk-1))
    blk_stripe_offset = (blkno + (blk_per_segment*target_stripe_id)) % blk_per_stripe
    parity_disk_id = target_stripe_id % ndisk
    target_disk_id = blk_stripe_offset / blk_per_segment
    if parity_disk_id <= target_disk_id:
      target_disk_id = target_disk_id + 1
    new_blkno = (target_stripe_id*blk_per_segment) + (blk_stripe_offset%blk_per_segment)

    # iterate blkcount
    current_disk_id = target_disk_id
    current_stripe_id = target_stripe_id
    current_blkno = new_blkno
    current_blkcount = blkcount
    next_segment_blk = (current_stripe_id+1)*blk_per_segment
    
    max_blkcount_segment = 0
    min_blkno_segment = current_blkno

    while blkcount > 0:
      if current_blkcount + current_blkno > next_segment_blk:
        current_blkcount = next_segment_blk-current_blkno

      if firstline[current_disk_id] is False:
        outtraces[current_disk_id].write("\n")
      else:
        firstline[current_disk_id] = False
      outtraces[current_disk_id].write("{} {} {} {} {}".format(time, devno, current_blkno, current_blkcount, operation))
      
      if max_blkcount_segment < current_blkcount: 
        max_blkcount_segment = current_blkcount

      # move to next segment and skip parity segment
      while True:
        current_disk_id = current_disk_id + 1
        if current_disk_id == ndisk:
          # write parity before change to next stripe
          if operation == 0:
            if firstline[current_stripe_id%ndisk] is False:
              outtraces[current_stripe_id%ndisk].write("\n")
            else:
              firstline[current_stripe_id%ndisk] = False
            outtraces[current_stripe_id%ndisk].write("{} {} {} {} {}".format(time, devno, min_blkno_segment, max_blkcount_segment, operation))
          current_disk_id = 0
          current_stripe_id = current_stripe_id + 1
        if current_disk_id != current_stripe_id%ndisk:
          current_blkno = current_stripe_id * blk_per_segment
          min_blkno_segment = current_blkno
          break

      blkcount = blkcount - current_blkcount
      next_segment_blk = (current_stripe_id+1)*blk_per_segment

  for i in range (0,ndisk):
    outtraces[i].close()
  intrace.close()