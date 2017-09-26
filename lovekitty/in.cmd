pyinstaller --noconfirm --log-level=WARN ^
    --onedir -c ^
    --add-data="img;img" ^
    --icon=logo.ico ^
	--name=kitty ^
    main.py