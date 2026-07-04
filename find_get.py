import glob
for f in glob.glob("views/**/*.py", recursive=True):
    for i, line in enumerate(open(f, encoding="utf-8", errors="ignore")):
        if ".get(" in line:
            print(f"{f}:{i+1}:{line.strip()}")
