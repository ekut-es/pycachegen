# Setup Verilator
## Packages Ubuntu 20.04 & WSL
```
sudo apt install git perl python3 make autoconf g++ flex bison ccache libgoogle-perftools-dev numactl perl-doc libfl2 libfl-dev zlibc zlib1g zlib1g-dev cmake ninja-build
```

## Packages macOS

```
brew install \
cmake \
ninja
brew install --HEAD randomplum/gtkwave/gtkwave
```

Add `$CPPFLAGS` and `LDFLAGS` to your `.zshrc`/`.bashrc`

```
export CPPFLAGS="-isysroot $(xcrun -show-sdk-path) ${CPPFLAGS}"
export LDFLAGS="-L$(xcrun -show-sdk-path)/usr/lib ${LDFLAGS}"
export VERILATOR_ROOT="$(brew --prefix verilator)"
```

### Install Bison from scratch

```
sudo mkdir -p /opt/bison/bison-3.7.91
wget http://alpha.gnu.org/gnu/bison/bison-3.7.91.tar.xz
tar -xvf bison-3.7.91.tar.xz
cd bison-3.7.91
./configure CFLAGS="-isysroot $(xcrun -show-sdk-path)" CPPFLAGS="-isysroot $(xcrun -show-sdk-path)" --prefix=/opt/bison/bison-3.7.91
make
sudo make install
```

Update environment variables for `bison` in your `.bashrc`/`.zshrc`:

```
export CPPFLAGS="-I/opt/bison/bison-3.7.91/share/include ${CPPFLAGS}"
export LDFLAGS="-L/opt/bison/bison-3.7.91/lib ${LDFLAGS}"
export PATH="/opt/bison/bison-3.7.91/bin:${PATH}"
```

### Install Flex from scratch

```
sudo mkdir /opt/flex/flex-2.6.4
wget https://github.com/westes/flex/releases/download/v2.6.4/flex-2.6.4.tar.gz
tar -xvf flex-2.6.4.tar.gz
cd flex-2.6.4
./configure CFLAGS="-isysroot $(xcrun -show-sdk-path)" CPPFLAGS="-isysroot $(xcrun -show-sdk-path)" --prefix=/opt/flex/flex-2.6.4
make
sudo make install
```

Update environment variables for `flex` in your `.bashrc`/`.zshrc`:

```
export CPPFLAGS="-I/opt/flex/flex-2.6.4/include ${CPPFLAGS}"
export LDFLAGS="-L/opt/flex/flex-2.6.4/lib ${LDFLAGS}"
export PATH="/opt/flex/flex-2.6.4/bin:${PATH}"
```

## Common

Clone ACADL repository outside of the project repository:
```
git clone git@es-git.cs.uni-tuebingen.de:es/genial/acadl.git PATH_TO_ACADL
```

# Build project for development
```
python -m venv .venv
source .venv/bin/activate
python -m pip install -e PATH_TO_ACADL
python -m pip install -e .\[dev\]
pre-commit install
```
