@echo off

for %%i in (requests colorama cryptography) do (
    python -c "import %%i" 2>nul || pip install %%i
)

python -c "import discord; print(discord.__version__)" 2>nul || (
    echo discord.py not found. Installing version 1.7.3...
    pip install discord.py==1.7.3
)

for /f "tokens=*" %%v in ('python -c "import discord; print(discord.__version__)"') do (
    if "%%v" neq "1.7.3" (
        echo discord.py version is %%v. Installing version 1.7.3...
        pip install discord.py==1.7.3
    )
)

python -c "import discord; print(discord.__version__)" 2>nul || (
    echo discord not found. Installing version 1.7.3...
    pip install discord==1.7.3
)

for /f "tokens=*" %%v in ('python -c "import discord; print(discord.__version__)"') do (
    if "%%v" neq "1.7.3" (
        echo discord version is %%v. Installing version 1.7.3...
        pip install discord==1.7.3
    )
)

echo All required packages are installed.
python main.py
pause