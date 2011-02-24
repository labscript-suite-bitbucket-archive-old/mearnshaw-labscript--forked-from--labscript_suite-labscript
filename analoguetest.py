from pylab import *
import time

def ramp(t,initial,duration,final):
    m = (final - initial)/float(duration) # be sure to prevent integer division!
    c = initial - m*t
    return lambda x: m*x + c

def sine(t,frequency):
    return lambda x: sin(x) + 0.5

def fastflatten(inarray):
    """A faster way of flattening our arrays than pylab.flatten.
    pylab.flatten returns a generator which takes a lot of time and memory
    to convert into a numpy array via array(list(generator)).  The problem
    is that generators don't know how many values they'll return until
    they're done. This algorithm produces a numpy array directly by
    first calculating what the length will be. It is several orders of
    magnitude faster. Note that we can't use numpy.ndarray.flatten here
    since our inarray is really a list of 1D arrays of varying length
    and/or single values, not a N-dimenional block of homogeneous data
    like a numpy array."""
    start_time = time.time()
    total_points = sum([len(element) if iterable(element) else 1 for element in inarray])
    flat = empty(total_points,dtype=float32)
    i = 0
    for val in inarray:
        if iterable(val):
            flat[i:i+len(val)] = val[:]
            i += len(val)
        else:
            flat[i] = val
            i += 1
    # compare to pylab.flatten():
#    print 'fastflatten(inarray):',time.time() - start_time
#    start_time = time.time()
#    flat = array(list(flatten(inarray)),dtype=float32)
#    print 'array(list(numpy.flatten(inarray))):',time.time() - start_time
    return flat
    
    
class IODevice:
    """This class represents a grouping of outputs (analogue or
    digital) that all share a common pseudoclock. When
    IODevice.make_instruction_table is called, instructions are collected
    from the IODevice's attached outputs, and arrays of values are
    generated for them to output on each clock tick, as well as
    instructions for the pseudo clock itself."""

    # Maximum clock rate of the pseudo clock. To be overridden by subclasses:
    clock_limit = 1e9
    
    def __init__(self,name,clock=None):
        self.outputs = []
        self.name = name
        self.clock = clock
        
    def collect_change_times(self):
        """Asks all connected outputs for a list of times that they
        change state. Takes the union of all of these times. Note
        that at this point, a change from holding-a-constant-value
        to ramping-through-values is considered a single state
        change. The clocking times will be filled in later in the
        expand_change_times function, and the ramp values filled in with
        expand_timeseries."""
        # use a set to avoid duplicates:
        self.change_times = set()
        for output in self.outputs:
            output.make_times()
            self.change_times = self.change_times.union(output.times)
        self.change_times = list(self.change_times)
        self.change_times.sort()
        
    def make_timeseries(self):
        """Instructs each connected output to construct a list of its
        states at each time in self.change_times, that is at any point in
        time that one or more connected outputs change state. By state,
        I don't mean the value of the output at that moment, rather
        I mean what instruction it has. This might be a single value,
        or it might be a reference to a function for a ramp etc."""
        for output in self.outputs:
            output.make_timeseries(self.change_times)
        
    def expand_change_times(self):
        """For each time interval delimited by self.change_times,
        constructs an array of times at which the clock for this device
        needs to tick. If the interval has all outputs having constant
        values, then only the start time is stored.  If one or more
        outputs are ramping, then the clock ticks at the maximum clock
        rate requested by any of the outputs. Also produces a higher
        level description of the clocking; self.clock. This list contains
        the information that facilitates programming a pseudo clock
        using loops."""
        self.all_times = []
        self.clock = []
        for i, time in enumerate(self.change_times):
            # what's the fastest clock rate?
            maxrate = 0
            for output in self.outputs:
                # Check if output is sweeping and has highest clock rate
                # so far. If so, store its clock rate to max_rate:
                if isinstance(output.timeseries[i],dict) and output.timeseries[i]['clock rate'] > maxrate:
                    # It does have the highest clock rate? Then store that rate to max_rate:
                    maxrate = output.timeseries[i]['clock rate']
            if maxrate:
                # If there was ramping at this timestep, how many clock ticks fit before the next instruction?
                n_ticks, remainder = divmod((self.change_times[i+1] - time)*maxrate,1)
                n_ticks = int(n_ticks)
                # Can we squeeze the final clock cycle in at the end?
                if remainder and remainder/float(maxrate) >= 1/float(self.clock_limit):
                    # Yes we can. Clock speed will be as
                    # requested. Otherwise the final clock cycle will
                    # be too  long, by the fraction 'remainder'.
                    n_ticks += 1
                duration = n_ticks/float(maxrate) # avoiding integer division
                self.all_times.append(array(linspace(time,time + duration,n_ticks,endpoint=False),dtype=float32))
                # Note that even though all arrays are single precision
                # floating point, the numbers stored to the clock list
                # below are double precision. This is important so that
                # rounding errors in the stepsize don't become significant
                # after many clock cycles.
                self.clock.append({'start': time, 'reps': n_ticks, 'step': 1/float(maxrate)}) # prevent integer division
            else:
                self.all_times.append(time)
                self.clock.append(time)
                
    def expand_timeseries(self):
        for output in self.outputs:
            output.make_outputarray(self.all_times)
            
    def make_raw_output(self):
        self.flat_times = fastflatten(self.all_times)
        del self.all_times
        for output in self.outputs:
            output.raw_output = fastflatten(output.outputarray)
            del output.outputarray
            
    def make_instruction_table(self):
        self.collect_change_times()
        self.make_timeseries()
        self.expand_change_times()
        self.expand_timeseries()
        self.make_raw_output()
#        print out the clock instructions:
#        print 'start','   step','    reps'
#        for thing in self.clock:
#            if isinstance(thing, dict):
#                print '%1f'%thing['start'], '%1f'%thing['step'], '%02d'%thing['reps']
#            else:
#                print round(thing,2)
 
class NIBoard:
    pass
       
class PulseBlaster(IODevice):
    def generate_code(self):
        self.make_instruction_table()
               
class Output:
    description = 'generic output'
    # Overridden by subclasses, for example {1:'open', 0:'closed'}
    allowed_states = {}
    
    def __init__(self,name,IO_device,outputnumber):
        self.name = name
        self.instructions = {}
        IO_device.outputs.append(self)
        
        
    def instruction_to_string(self,instruction):
        """gets a human readable description of an instruction"""
        if isinstance(instruction,dict):
            return instruction['description']
            #TODO Actually give instructions descriptions
        elif allowed_states:
            return allowed_states[instruction]
        else:
            return str(instruction)
        
    def add_instruction(self,time,instruction):
        #Check that this doesn't collide with previous instructions:
        if time in self.instructions.keys():
            print 'WARNING: State of', self.description, self.name, 'at t=%ss'%str(time),
            print 'has already been set to %s.'%self.instruction_to_string(self.instructions[t]),
            print 'Overwriting to %s.\n'%self.self.instruction_to_string(instruction)
        self.instructions[time] = instruction
        #TODO check that ramps don't collide
        
    def perform_checks(self):
        # Check if there are no instructions. Generate a warning and insert an
        # instruction telling the output to remain at zero.
        if not self.instructions:
            print 'WARNING:', self.name, 'has no instructions. It will be set to %s for all time.'%instructions_to_string(0)
            self.add_instruction(0,0)    
        # Check if there are no instructions at t=0. Generate a warning and insert an
        # instruction telling the output to start at zero.
        if 0 not in self.instructions.keys():
            print 'WARNING:', self.name, 'has no instructions at t=0. It will initially be set to %s.'%instructions_to_string(0)
            self.add_instruction(0,0)    
        # Check that ramps have instructions following them.
        # If they don't, insert an instruction telling them to hold their final value.
        for instruction in self.instructions.values():
            if isinstance(instruction, dict) and instruction['end time'] not in self.instructions.keys():
                self.add_instruction(instruction['end time'], instruction['function'](instruction['end time']))
            
    def make_times(self):
        self.perform_checks()
        self.times = self.instructions.keys()
        self.times.sort()
            
    def make_timeseries(self,change_times):
        self.timeseries = []
        i = 0
        for change_time in change_times:
            try:
                if i < len(self.times):
                    while change_time >= self.times[i]:
                        i += 1
            except IndexError:
                # We allow the index to go one higher, since we index self.times[i-1] below.  
                # Raise the error otherwise.
                if not i == len(self.times):
                    raise
            instruction = self.instructions[self.times[i-1]]
            if isinstance(instruction, dict) and instruction['end time'] <= change_time:
                print 'detected that a ramp has ended!' 
                instruction = instruction['function'](instruction['end time'])
            self.timeseries.append(instruction)     
    
    def make_outputarray(self,all_times):
        self.outputarray = []
        for i, time in enumerate(all_times):
            if iterable(time):
                if isinstance(self.timeseries[i],dict):
                    midpoints = time + 0.5*(time[1] - time[0])
                    next_time = all_times[i+1][0] if iterable(all_times[i+1]) else all_times[i+1]
                    midpoints[-1] = time[-1] + 0.5*(next_time - time[-1])
                    outarray = self.timeseries[i]['function'](midpoints)
                else:
                    outarray = empty(len(time),dtype=float32)
                    outarray.fill(self.timeseries[i])
                self.outputarray.append(outarray)
            else:
                self.outputarray.append(self.timeseries[i])
    

def discretise(t,y):
    tnew = zeros((len(t),2))
    ynew = zeros((len(y),2))

    tnew[:,0] = t[:]
    tnew[:-1,1] = t[1:]
    tnew= tnew.flatten()[:-1]

    ynew[:,0] = y[:]
    ynew[:,1] = y[:]
    ynew= ynew.flatten()[:-1]
    return tnew, ynew

def plot_all(device):
    
    colours = ['r','b','g']
#    for tick in device.flat_times:
#        axvline(tick,color='k',linestyle='-')
    for i, output in enumerate(device.outputs):
        t,y = discretise(device1.flat_times,output.raw_output)
        plot(t,y,colours[i]+'-',label=output.name)
    t = linspace(0,10,1000)
    plot(t,sine(0,1)(t),'k')

    grid(True)
    xlabel('time (seconds)')
    ylabel('analogue output values')
    title('Putting analogue outputs on a common clock')
    legend(loc='lower right')
    axis([0,10,-1,5.5])
    show()
    
import time
start_time = time.time()

device1 = IODevice('device 1')

output1 = Output('output 1',device1,1)
output2 = Output('output 2',device1,2)
output3 = Output('output 3',device1,3)

output1.add_instruction(0,2)
output1.add_instruction(1, {'function': ramp(1,2,2,3), 'end time' : 3, 'clock rate':  5})

output2.add_instruction(0,3)
output2.add_instruction(2, {'function': ramp(2,3,3,4), 'end time' : 5, 'clock rate': 10})
output2.add_instruction(5.9,5)
output2.add_instruction(7,4)
output2.add_instruction(8,5)
output3.add_instruction(0, {'function': sine(0,1), 'end time' : 10, 'clock rate':    3})

device1.make_instruction_table()
#print time.time() - start_time
plot_all(device1)

#count how many numbers are in memory
#count = 0
#for obj in ['device1','output1','output2','output3']:
#    for thing in dir(eval(obj)):
#        if eval('type(%s.%s) == ndarray'%(obj,thing)):
#            thingcount = eval('len(%s.%s)'%(obj,thing))
#            count += thingcount
#            print '%s.%s'%(obj,thing), thingcount, 'floats'
#print count, 'total floats in memory'



