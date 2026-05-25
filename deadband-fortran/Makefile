FC = gfortran
FFLAGS = -O3 -march=native -ffast-math -Wall -Wextra
TARGET = test_deadband

all: $(TARGET)

$(TARGET): deadband.f90 test_deadband.f90
	$(FC) $(FFLAGS) -o $@ $^

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET) *.mod

.PHONY: all run clean
