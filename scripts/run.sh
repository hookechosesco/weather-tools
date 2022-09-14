while true
do
read -p "What do you want to do? 
[1] metar
[2] skewt
[3] meteogram
[4] GOES
--> " choice

# read choice

if [[ $choice -eq 1 ]]; then ./metar.py
elif [[ $choice -eq 2 ]]; then ./skewt.py
elif [[ $choice -eq 3 ]]; then ./meteogram.py
elif [[ $choice -eq 4 ]]; then ./goes_imagery.py
else echo "Enter a valid option"
fi
echo ""
done