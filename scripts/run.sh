while true
do
read -p "What do you want to do?
[1] METAR
[2] TAF
[3] Skew T
[4] Meteogram
[5] GOES
--> " choice

if [[ $choice -eq 1 ]]; then python metar.py
elif [[ $choice -eq 2 ]]; then python taf.py
elif [[ $choice -eq 3 ]]; then python skewt.py
elif [[ $choice -eq 4 ]]; then python meteogram.py
elif [[ $choice -eq 5 ]]; then python goes_imagery.py
else echo "Enter a valid choice"
fi
echo ""
done