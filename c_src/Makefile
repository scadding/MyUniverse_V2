

SUBDIRS=1MioStars ExtSys SectorMaker Stars worldgen accrete GenSec4 planetgen planet_old Planets stargen SysGen4

all:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $$dir; \
	done

clean:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $$dir clean; \
	done
