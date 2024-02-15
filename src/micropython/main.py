'''
Created on Jan 9, 2024

@author: Pat Deegan
@copyright: Copyright (C) 2024 Pat Deegan, https://psychogenic.com

Modified by Ioannis-Rafail Tzonevrakis to include tests for the
tt_um_cam project.
'''

import ttboard.util.time as time
from ttboard.mode import RPMode
from ttboard.demoboard import DemoBoard
from ttboard.pins.gpio_map import GPIOMap
import random
from math import ceil

# Parameters
# Clock frequency for native clock test
NATIVE_CLK = 0.1e6
# Clock period in μs (automatically calculated)
NATIVE_CLK_PERIOD_US = ceil(1/NATIVE_CLK*1e6)
# Delay between clock signal toggles when manually stepping the clock
# in ms
SINGLE_STEP_MS_DELAY = 1
# Number of cycles to spend in reset
N_CYCLES_IN_RESET = 4

# Pin import to provide access in REPL
# to things like tt.uio3.mode = Pin.OUT
from ttboard.pins.upython import Pin

tt = None
startup_with_clock_high = False
def startup():
    global tt, startup_with_clock_high
    
    # take a look at project clock pin on startup
    # make note if it was HIGH
    clkPin = Pin(GPIOMap.RP_PROJCLK, Pin.IN)
    startup_with_clock_high = clkPin()
    
    # construct DemoBoard
    # either pass an appropriate RPMode, e.g. RPMode.ASIC_ON_BOARD
    # or have "mode = ASIC_ON_BOARD" in ini DEFAULT section
    tt = DemoBoard()

    
    print("\n\n")
    print("The 'tt' object is available.")
    print()
    print("Projects may be enabled with tt.shuttle.PROJECT_NAME.enable(), e.g.")
    print("tt.shuttle.tt_um_urish_simon.enable()")
    print()
    print("Pins may be accessed by name, e.g. tt.out3() to read or tt.in5(1) to write.")
    print("Config of pins may be done using mode attribute, e.g. ")
    print("tt.uio3.mode = Pins.OUT")
    print("\n\n")

def cam_write_byte(value: int):
        if value > 127:
            raise ValueError('CAM only accepts 7-bit values')
        tt.input_byte = value | (1 << 7)
        tt.clock_project_once(msDelay=SINGLE_STEP_MS_DELAY)
        tt.input_byte = 0
        tt.clock_project_once(msDelay=SINGLE_STEP_MS_DELAY)

def cam_get_found_addr():
    return tt.bidir_byte | (tt.output_byte << 8)

def cam_lookup(value: int):
    if value > 127:
            raise ValueError('CAM only accepts 7-bit values')
    tt.input_byte = value
    if tt.is_auto_clocking:
        # Wait for 2*Period for inputs to stabilize, so that we can
        # (hopefully) take into account any instabilities in the 
        # rp2040/mpy timer....
        time.sleep_us(2*NATIVE_CLK_PERIOD_US)
    else:
        tt.clock_project_once(msDelay=SINGLE_STEP_MS_DELAY)
    return cam_get_found_addr()

def test_cam_lookup(value: int, expected_result: int):
    result = cam_lookup(value)
    if result != expected_result:
        print(f'For input 0x{value: X} expected output 0x{expected_result: X}, got 0x{result: X}')
        return False
    
    return True

def reset_project(n_cycles_in_reset: int=
                  N_CYCLES_IN_RESET):
    """Resets the project."""
    # Different handling in autoclocking vs single-stepping mode
    if tt.is_auto_clocking:
        tt.reset_project(True)
        time.sleep_us(N_CYCLES_IN_RESET*NATIVE_CLK_PERIOD_US)
        tt.reset_project(False)
        time.sleep_us(2*NATIVE_CLK_PERIOD_US)
    else:
        tt.reset_project(True)
        for _ in range(n_cycles_in_reset):
            tt.clock_project_once(msDelay=SINGLE_STEP_MS_DELAY)
        tt.reset_project(False)
        # Spend an additional clock with reset deasserted
        tt.clock_project_once(msDelay=SINGLE_STEP_MS_DELAY)


def test_post_reset():
    """Post-reset behavior test. Assumes autoclocking."""

    # Reset project and inputs
    tt.clock_project_PWM(NATIVE_CLK)
    reset_project()

    # Check if all positions are zero
    result = test_cam_lookup(value=0, expected_result=0xffff)
    
    tt.clock_project_stop()

    return result

def test_post_reset_misses():
    """Tests that misses behave correctly after reset. 
       Assumes autoclocking."""
    tt.clock_project_PWM(NATIVE_CLK)
    reset_project()

    passed = True
    for i in range(1, 127):
        passed = test_cam_lookup(value=i, expected_result=0x00) and passed
    
    tt.clock_project_stop()

    return passed

def test_simple_writes():
    """Tests simple writes to the CAM. Uses manual clock stepping."""

    tt.clock_project_stop()
    reset_project()
    test_passed = True

    # Perform some writes
    cam_write_byte(0x01)
    cam_write_byte(0x7a)
    cam_write_byte(0x0a)
    cam_write_byte(0x7a)

    # See if we get the expected results
    for value, expected in ((0x7a, 0x0a),
                            (0x01, 0x01),
                            (0x0a, 0x04)):
        test_passed = (test_cam_lookup(value=value, 
                                       expected_result=expected) and
                       test_passed)
    
    return test_passed

def test_fill_up_then_read():
    """Tests reading after filling up the CAM. Uses manual clock stepping."""

    tt.clock_project_stop()
    reset_project()

    for i in range(1, 17):
        cam_write_byte(i)

    test_passed = True

    for i in range(1, 17):
        expected_result = 1 << (i-1)
        test_passed = (test_cam_lookup(value=i,
                                       expected_result=expected_result) and
                        test_passed)
    
    return test_passed

def test_random_rw():
    """Tests randomly reading from and writing to the CAM. Uses manual
       clock stepping."""
    
    tt.clock_project_stop()
    reset_project()
    
    current_position = 0
    memory_contents = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    test_passed = True

    for i in range(5000):
        # 50% reads, 50% writes
        rv = random.random()
        if rv < 0.5:
            write = True
        else:
            write = False
    
        if write:
            # If we are performing a write, send it out and record it in 
            # memory_contents:
            value_to_write = random.randint(0, 127)
            cam_write_byte(value_to_write)
            memory_contents[current_position] = value_to_write
            if current_position == 15:
                current_position = 0
            else:
                current_position += 1
        else:
            # We are performing a read; decide whether to send a hit or a miss
            # (10% misses)
            rv = random.random()
            if rv < 0.1:
                miss = True
            else:
                miss = False

            # Find a value to read        
            if miss:
                # We need to perform a miss, find a value not in memory
                expected_result = 0
                while True:
                    value_to_read = random.randint(0, 127)
                    if value_to_read not in memory_contents:
                        break
            else:
                # Else randomly pick a value we know is in memory, and
                # compute the expected result
                value_to_read = memory_contents[random.randint(0, 15)]
                expected_bits_on = [i for i in range(len(memory_contents)) \
                                    if memory_contents[i] == value_to_read]
                expected_result = 0
                for bitpos in expected_bits_on:
                    expected_result = expected_result | (1 << bitpos)

            test_passed = (test_cam_lookup(value=value_to_read,
                                           expected_result=expected_result) 
                           and test_passed)
    
    return test_passed


def test_random_write_and_read_at_native():
    """Tests random writing (at single-stepping) then reading at native
       clock frequency.
    """

    reset_project()

    test_passed = True

    for n_iterations in range(10):
        tt.clock_project_stop()
        memory_contents = []

        for i in range(16):
            memory_contents.append(random.randint(0, 127))
            cam_write_byte(memory_contents[-1])
        
        tt.clock_project_PWM(NATIVE_CLK)

        for n_reads in range(500):
            rv = random.random()
            if rv < 0.1:
                miss = True
            else:
                miss = False

            if miss:
                expected_result = 0
                while True:
                    value_to_read = random.randint(0, 127)
                    if value_to_read not in memory_contents:
                        break
            else:
                value_to_read = memory_contents[random.randint(0, 15)]
                expected_bits_on = [i for i in range(len(memory_contents)) \
                                    if memory_contents[i] == value_to_read]
                expected_result = 0
                for bitpos in expected_bits_on:
                    expected_result = expected_result | (1 << bitpos)
        
            test_passed = (test_cam_lookup(value=value_to_read,
                                           expected_result=expected_result)
                           and test_passed)
    
    return test_passed

# Tuple of (test_function, test_purpose)
tests = ((test_post_reset, 'Post-reset behavior'),
         (test_post_reset_misses, 'Post-reset misses'),
         (test_simple_writes, 'Simple writes'),
         (test_fill_up_then_read, 'Reading after filling up'),
         (test_random_rw, 'Random reads and writes'),
         (test_random_write_and_read_at_native, 
          'Random writes, then reads at native clock'))

startup()

# Enable project
tt.shuttle.tt_um_cam.enable()

# Clock at a slow rate to prevent wokwi from grinding to a halt
tt.clock_project_PWM(0.1e6)

# Initial reset
reset_project()

# Run tests
for i, test in enumerate(tests):
    test_function, test_purpose = test
    print(f'Test {i}: {test_purpose}...', end=' ')
    if test_function():
        print('[PASS]')
    else:
        print('[FAIL]')