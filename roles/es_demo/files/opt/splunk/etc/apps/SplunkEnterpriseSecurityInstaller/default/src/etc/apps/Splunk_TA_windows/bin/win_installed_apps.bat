@echo off
REM --------------------------------------------------------
REM Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
REM --------------------------------------------------------

setlocal EnableDelayedExpansion

REM For each app key, print out the name of the app and any parameters under the entry
for /f "tokens=*" %%G in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" ^| findstr "Uninstall\\"') do (call :output_reg "%%G")
goto :eof

:output_reg

	REM Echo an empty line to indicate that this is a new entry
	@echo.
	
	REM Get the current date into a variable
	for /f "tokens=*" %%A in ('date /t') do for %%B in (%%A) do set date=%%B
	
	REM Get the current time into a variable
	set time = 'time /t'
	for /f "tokens=1,2 delims=." %%A in ("%time%") do set time=%%A
	
	REM Print out the date & time
	@echo %date% %time%
	
	REM Add the enumerated key
	@echo Installed application enumerated from %1
	
	REM Get the name of the app from the last segment in the registry path
	set app_name=%1
	
	REM Strips out the first 72 characters of the path in order to get just the app name
	set app_name=%app_name:~72,150%
	
	REM Strip the last quote
	set app_name=%app_name:~0,-1% 
	
	REM Store a count value so that we can avoid printing the first entry
	set count=0
	
	REM This variable determines if the display name was found
	set display_name_found=0
	
	REM Now get the sub-keys
	for /F "tokens=1,2*" %%A in ('reg query %1') do (
		set /a count+=1
		
		REM Skip the entry if it just repeats the name we are querying for or if it is blank or if is "<NO" (which indicates the item has no name)
		if not "%%A" == %1 if not "%%A" == "" if not "%%A" == "<NO" echo %%A=%%C
		
		REM Note that the display name was already found
		if %%A==DisplayName set /a display_name_found=1
	)
	
	REM If the display name was not found, then use the name of the registry path name instead
	if !display_name_found!==0 echo DisplayName=%app_name%
