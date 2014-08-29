@echo off
REM --------------------------------------------------------
REM Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
REM --------------------------------------------------------

setlocal EnableDelayedExpansion

REM Get the current date into a variable
for /f "tokens=*" %%A in ('date /t') do for %%B in (%%A) do set date=%%B

REM Get the current time into a variable
set time = 'time /t'
for /f "tokens=1,2 delims=." %%A in ("%time%") do set time=%%A

REM Get the date & time
set date_time=%date% %time%

REM Get the list of open ports by running netstat and filtering the results to those that contain actual ports (dropping the header)
for /f "tokens=*" %%G in ('netstat -nao ^| findstr /r "LISTENING"') do (call :output_ports "%%G")
goto :eof

:output_ports
	
	REM Parse the ports list
	for /f "tokens=1,2,4,5 delims= " %%A in (%1) do (
		set protocol=%%A
		set dest=%%B
		set status=%%C
		set pid=%%D
	)
	
	REM Skip the header
	if "!protocol!"=="Proto" goto :eof
	if "!protocol!"=="Active" goto :eof
	
	REM Parse the each port
	for /f "tokens=1,2,3 delims=:" %%A in ("%dest%") do (
		set dest_ip=%%A
		set dest_port=%%B
		set alt_dest_port=%%C
		
		REM Some entries will exist in the [::]:0 format and thus throw off the parsing. Correct for this: 
		if "!dest_port!" == "]" set dest_port=!alt_dest_port!
	)
	
	REM Replace the dest IP with the empty IP range if necessary
	if "!dest_ip!"=="[" set dest_ip=[::]

	REM Print out the result
	echo %date_time% transport=%protocol% dest_ip=%dest_ip% dest_port=%dest_port% pid=!pid!
	