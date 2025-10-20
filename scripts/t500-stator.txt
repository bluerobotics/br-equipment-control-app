### T500 STATOR ###
gantry.home_z
gantry.home_x, gantry.home_y
fillhead.machine_home
fillhead.vac_valve_home_tubed, fillhead.inj_valve_home_tubed
fillhead.cartridge_home
fillhead.inj_valve_close

fillhead.heater_on 70 C
gantry.move_x 524 mm, gantry.move_y 41 mm
gantry.move_z -62 mm
gantry.move_z -68 mm 2 mm/s    
fillhead.vacuum_on
fillhead.vac_valve_open
wait 5 sec
fillhead.vacuum_leak_test
WAIT_UNTIL_HEATER_AT_TEMP 65 C
VACUUM_ON
INJECTION_VALVE_OPEN
INJECT_STATOR 30 ml 0.4 ml/s
WAIT 5 sec
INJECT_STATOR 15 ml 0.2 ml/s
VACUUM_VALVE_CLOSE
WAIT 10 sec
INJECTION_VALVE_CLOSE
WAIT 10 sec
MOVE_Z -62 mm 1 mm/s
MOVE_Z -55 mm 4 mm/s
VACUUM_OFF
HEATER_OFF
MOVE_Z 0 mm

# PURGE ROUTINE
MOVE_X 400 mm, MOVE_Y 41 mm

CYCLE 100 times:
    INJECTION_VALVE_OPEN
	INJECT_STATOR 5 ml 0.2 ml/s
	INJECTION_VALVE_CLOSE
	WAIT 200 sec

CYCLE 200 times:
    WAIT 1 sec
    CYCLE 2 times:
        WAIT 1 sec

WAIT 100 sec

MACHINE_HOME_MOVE
INJECTION_VALVE_HOME_UNTUBED
INJECTION_VALVE_CLOSE

INJECTION_VALVE_OPEN

MOVE_X 400 mm



































PRESSBOI_MOVE 




























