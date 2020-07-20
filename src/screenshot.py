#!/usr/bin/env python3

import matplotlib.pyplot as plt

from gw_com_1kb import com
from gw_lan import lan
import dso1kb

#Check interface according to config file or command line argument.
# port=com.scanComPort()

#Connecting to a DSO.
dso=dso1kb.Dso("10.10.0.77:3001")
#dso=dso1kb.Dso("127.0.0.1:3001")

# for i in range(1,5):
#     print(i, dso.isChannelOn(i))

# dso.write(":CHAN1:DISP ON\n")
# dso.write(":CHAN2:DISP ON\n")
# dso.write(":CHAN3:DISP OFF\n")
# dso.write(":CHAN4:DISP OFF\n")
#
# dso.getRawData(True, 1)


dso.write(':DISP:OUTP?\n')                 #Send command to get image from DSO.

# dso.write(':DISP:PNGOutput?\n')            #Send command to get image from DSO.
dso.getBlockData()
dso.ImageDecode(1)
# self.showImage()
# plt.tight_layout(True)

plt.imshow(dso.im)
plt.show()
