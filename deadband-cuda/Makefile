# Deadband CUDA — Makefile
# Target: NVIDIA GeForce RTX 4050 Laptop GPU (sm_89)

CUDA_PATH ?= /usr/local/cuda-12.6
NVCC      := $(CUDA_PATH)/bin/nvcc
ARCH      := sm_89
NVCCFLAGS := -arch=$(ARCH) -O2 -lineinfo
LIBS      := -lcurand -lcuda

SRCS := eisenstein_snap.cu hpdf_dither.cu deadband_check.cu swarm_sim.cu benchmark.cu
TARGET := benchmark

.PHONY: all clean run

all: $(TARGET)

$(TARGET): $(SRCS) deadband_cuda.h
	$(NVCC) $(NVCCFLAGS) -o $@ $(SRCS) $(LIBS)

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET) *.o
