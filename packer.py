import tarfile
tar = tarfile.open("storage.tar.gz", "w:gz")
for name in [".config"]:
    tar.add(name)
tar.close()
