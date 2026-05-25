CC      = gcc
CFLAGS  = -O3 -mavx2 -Wall -Wextra -std=c11
LDFLAGS = -lm

SRCS    = eisenstein.c hpdf.c div360.c bma.c deadband.c shell.c fib_spline.c
OBJS    = $(SRCS:.c=.o)

all: test_deadband

test_deadband: test_deadband.c $(OBJS) deadband.h
	$(CC) $(CFLAGS) -o $@ test_deadband.c $(OBJS) $(LDFLAGS)

%.o: %.c deadband.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f *.o test_deadband

.PHONY: all clean
