mkdir C:/dumps
procdump -accepteula -ma -i C:/dumps
write-host "Dumps will be written to C:/dumps" -ForegroundColor Black -BackgroundColor DarkYellow
