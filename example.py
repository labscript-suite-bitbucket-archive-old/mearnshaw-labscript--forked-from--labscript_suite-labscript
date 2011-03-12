import time
import shutil
very_start_time = time.time()
import os
shutil.copy('dummy_template.h5', 'dummy.h5')

############################################################################################
start_time = time.time()
from labscript import *
labscriptimport =  time.time() - start_time
start_time = time.time()

pulseblaster1 = PulseBlaster('PulseBlaster')
NI_board1 = NIBoard('NI PCI-6733', pulseblaster1,'fast')
novatech1 = NovaTechDDS9M('Novatech DDS', pulseblaster1,'slow')

analogue1 = AnalogueOut('output 1', NI_board1,'ao0')
analogue2 = AnalogueOut('output 2', NI_board1,'ao1')
analogue3 = AnalogueOut('output 3', NI_board1,'ao2')
shutter1 = Shutter('shutter 1', NI_board1, 'p0.0')
shutter2 = Shutter('shutter 2', pulseblaster1, 0)
dds1 = DDS('DDS 1', novatech1,0)
dds2 = DDS('DDS 2', novatech1,1)

t = 0
dds1.setamp(t,0.5)
dds1.setfreq(t,0.6)
dds1.setphase(t,0.7)
dds2.setamp(t,0.8)
dds2.setfreq(t,0.9)
dds2.setphase(t,1.0)

shutter1.close(t)
shutter2.close(t)
analogue1.constant(t,2)
analogue2.constant(t,3)
analogue3.sine(t,duration=10,amplitude=10,angfreq=2,phase=0,dc_offset=0.0,samplerate=1.5e5)
t = 1
shutter2.open(t)
analogue1.ramp(t, duration=2, initial=2, final=3, samplerate=1.5e5)

analogue2.ramp(t=2, duration=3, initial=3, final=4, samplerate=1.5e5)
shutter1.open(t=5.89)
analogue2.constant(t=5.9,value=5)
analogue2.constant(t=7,value=4)
analogue2.constant(t=8,value=5)

start_time = time.time()
stop(t=10)
generate_code()
#############################################################################################
print "from labscript import *: \t",round(labscriptimport,2),'sec'
print "generate_code():         \t", round(time.time() - start_time,2),'sec'
start_time = time.time()
os.system('sync') # linux only to measure hard drive write time, which is otherwise deferred.
print "os.system('sync'):       \t", round(time.time() - start_time,2),'sec'
print "total time:              \t", round(time.time() - very_start_time,2),'sec'
print 'hdf5 file size:          \t', round(os.path.getsize('dummy.h5')/(1024.0**2),1), 'MB'
print
#plot_outputs()
