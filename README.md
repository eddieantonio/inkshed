# Inkshed

A command line app that sets up a template and lets me write freely. It used
to be a really simple shell function:
    
```sh
inkshed () {
	filename="E.Santos.Inkshed.$1" 
	echo "% Inkshed $1\n% Eddie Santos" > $filename.md
	vim $filename.md && pandoc -S $filename.md -o $filename.docx
}
```

Haha! That would be just too simple and useful for me!

# License

Copyright (c) 2014 Eddie Antonio Santos. MIT licensed.

