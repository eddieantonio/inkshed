# Inkshed

A command line app that sets up a template and lets me write freely. It used
to be a really simple shell function:
    
	inkshed () {
		filename="E.Santos.Inkshed.$1" 
		echo "% Inkshed $1\n% Eddie Santos" > $filename.md
		vim $filename.md && pandoc -S $filename.md -o $filename.docx
	}

