from cx_Freeze import setup, Executable

executables = [
    Executable("main.py")
]

build_options = {
    "packages": [
        "random",
        "selenium",
        "dotenv",
        "os",
        "time",
        "yaspin",
        "fake_useragent",
        "bs4",
        "requests",
        "urllib.parse"
    ],
    "include_files": [],
}

setup(
    name="NextDoor-Scraper",
    version="1.0",
    description="NextDoor Scraper",
    options={"build_exe": build_options},
    executables=executables
)

