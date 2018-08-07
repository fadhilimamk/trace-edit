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
  for i in range (0,ndisk):
    outfile = open("out/"+infile+"-raid5disk" + str(i) + ".trace", "w")
    new_trace = createRaid5Subtrace(infile, i, ndisk, segment_size)
    
    for x in new_trace:
      outfile.write(x)

    outfile.close()


def createRaid5Subtrace(original_trace, diskid, ndisk, segment_size):
    out = []
    blk_size = 4096 # or sector size in hdd (in bytes)
    blk_per_segment = segment_size / blk_size
    blk_per_stripe = blk_per_segment * ndisk

    old_trace = open("in/" + original_trace)
    for line in old_trace:
      token = line.split(" ")
      time = token[0]
      devno = token[1]
      blkno = int(token[2].strip())
      blkcount = int(token[3].strip())
      operation = token[4]

      # calculating new blkno
      target_stripe_id = blkno / (blk_per_segment * (ndisk-1))
      blk_stripe_offset = (blkno + (blk_per_segment*target_stripe_id)) % blk_per_stripe
      parity_disk_id = target_stripe_id % ndisk
      target_disk_id = blk_stripe_offset / blk_per_segment
      if parity_disk_id <= target_disk_id:
        target_disk_id = target_disk_id + 1
      new_blkno = (target_stripe_id*blk_per_segment) + (blk_stripe_offset%blk_per_segment)

      while True:
        if target_disk_id == diskid and blkcount != 0:
          out.append("{} {} {} {} {}".format(time, devno, new_blkno, blkcount, operation))

        # make write commands to parity disk
        
        if blkcount <= blk_per_segment:
          break
        
        # need to write to the next segment
        else:
          blkcount = blkcount - blk_per_segment
          target_disk_id = target_disk_id + 1
          
          # handle edge of stripe
          if target_disk_id == ndisk:
            target_disk_id = 0
            target_stripe_id = target_stripe_id + 1

          # jump parity disk
          if target_disk_id == target_stripe_id % ndisk:
            target_disk_id = target_disk_id + 1

    return out

