# Chaoslauncher FPC build targets (Windows)
# Usage examples:
#   make multiinstance
#   make clean

FPC ?= fpc

LAZARUS_ROOT ?= D:\\lib\\lazarus2.2

FPC_FLAGS = -Mdelphi -dLCL -dLCLwin32 \
	-Fi"$(LAZARUS_ROOT)\\lcl\\include" \
	-Fi"$(LAZARUS_ROOT)\\lcl\\interfaces\\win32" \
	-Fu"$(LAZARUS_ROOT)\\lcl\\interfaces\\win32" \
	-Fu"$(LAZARUS_ROOT)\\lcl\\units\\i386-win32" \
	-Fu"$(LAZARUS_ROOT)\\lcl\\units\\i386-win32\\win32" \
	-Fu"$(LAZARUS_ROOT)\\components\\lazutils\\lib\\i386-win32" \
	-Fu"./Plugins" \
	-Fu"../../Common" \
	-Fu"../../../External/dcp" \
	-Fu"../../../External/dcp/hashes" \
	-Fu"../../../External/lockbox"

TARGET = Chaoslauncher.exe
TARGET_MULTI = Chaoslauncher - MultiInstance.exe

.PHONY: all build multiinstance clean

all: build

build:
	$(FPC) $(FPC_FLAGS) Chaoslauncher.dpr

multiinstance: build
	cp -f "$(TARGET)" "$(TARGET_MULTI)"

clean:
	del /Q /F "*.o" "*.ppu" "*.or" "*.compiled" "$(TARGET)" "$(TARGET_MULTI)" 2>nul || ver > nul
