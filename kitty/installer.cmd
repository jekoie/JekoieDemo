pyinstaller --noconfirm	^
    --onefile  ^
	--windowed  ^
    --add-data="img;img" ^
    --add-data="logo.jpg;." ^
	--add-data="qus.xml;." ^
	--add-data="kitty.ico;." ^
	--name="Kitty" ^
	--icon="kitty.ico" ^
    main.py
	
