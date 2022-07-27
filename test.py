DATA_WIDTH = 32
NUM_REGISTERS = 3
READ_WRITE_PORTS = 2

print(f"data_i: [0:{DATA_WIDTH*READ_WRITE_PORTS*NUM_REGISTERS-1}]")

for i in range(0, NUM_REGISTERS):
    for j in range(0, READ_WRITE_PORTS):
        print(
            f"i={i},j={j}: [{(READ_WRITE_PORTS*i+j)*DATA_WIDTH}:{(READ_WRITE_PORTS*i+j+1)*DATA_WIDTH-1}]"
        )
