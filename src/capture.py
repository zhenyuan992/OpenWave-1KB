#!/usr/bin/env python3

from gw_com_1kb import com
from gw_lan import lan
import dso1kb

#Check interface according to config file or command line argument.
port=com.scanComPort()

#Connecting to a DSO.
dso=dso1kb.Dso(port)

for i in range(1,5):
    print(i, dso.isChannelOn(i))

dso.write(":CHAN1:DISP ON\n")
dso.write(":CHAN2:DISP OFF\n")
dso.write(":CHAN3:DISP OFF\n")
dso.write(":CHAN4:DISP OFF\n")

dso.getRawData(True, 1)
