EXE = progska
SRC = progska.c netc.c th.c
INC = -I.
SNAPSHOT = progska-snapshot
ARCHIVE = $(SNAPSHOT).tar.gz

PREFIX = /usr/local

TAR = tar
CC = gcc
INSTALL = install
RM = rm -f
LN = ln -s

CFLAGS = -Wall
CFLAGS = -O2
#CFLAGS += -DDEBUG

OBJ = $(patsubst %.c,%.o,$(SRC))
all: $(EXE)

$(EXE): $(OBJ)
	$(CC) -o $@ $^ $(LIB)

clean: 
	$(RM) $(EXE) *.o $(ARCHIVE) $(SNAPSHOT)

package: clean
	$(LN) . $(SNAPSHOT)
	$(TAR) -czvf $(ARCHIVE) $(SNAPSHOT)/*
	$(RM) $(SNAPSHOT)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@ $(INC)

install: all
	$(INSTALL) $(EXE) $(PREFIX)/bin
