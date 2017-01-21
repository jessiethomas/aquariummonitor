$ErrorActionPreference="Stop"

#remove all temp files
Remove-Item "*.temp.txt" -Force -Recurse -ErrorAction SilentlyContinue

#create remote command to create folder
$comm = "command.temp.txt"
"rm -rf aquamonitor && mkdir aquamonitor" | Out-File $comm -Encoding ASCII

#create folder on pi
putty.exe -ssh pi@192.168.1.159 -pw raspberry -m $comm -sessionlog cmd.temp.txt | Out-Null
echo "Logs for creating folder..."
cat ./cmd.temp.txt
echo ""

#copy files locally to pi
pscp.exe -p -r  * pi@192.168.1.159:aquamonitor/

#run remote command to setup service
Remove-Item cmd.temp.txt -Force -ErrorAction SilentlyContinue
"cd aquamonitor && chmod +x raspberrypi_setup.sh && dos2unix **/* ** && sudo sh -c ./raspberrypi_setup.sh" | Out-File $comm -Encoding ASCII -Force
putty.exe -ssh pi@192.168.1.159 -pw raspberry -m $comm -sessionlog cmd.temp.txt -t | Out-Null
echo "Logs for running raspberrypi_setup.sh on pi"
cat cmd.temp.txt

#remove all temp files
Remove-Item "*.temp.txt" -Force -Recurse -ErrorAction SilentlyContinue