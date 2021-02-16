import tarfile
tar = tarfile.open("storage.tar.gz", "w:gz")
for name in ["storage"]:
    tar.add(name)
tar.close()
