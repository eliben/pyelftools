METADATA = {"type":"rpm","name":"coreutils","version":"9.7-8.fc43","architecture":"x86_64","osCpe":"cpe:/o:fedoraproject:fedora:43"}

main.elf: main.c
	gcc -O0 main.c -Xlinker '--package-metadata=$(METADATA)' -o main.elf
