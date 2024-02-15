# Test micropython firmware development for tt03p5-content-addressable-memory

## Requirements

* emscripten
* oss-cad-suite

## How to use

1. Compile the custom chip WASM with `make`
2. Open `diagram.json` with wokwi VsCode
3. Copy the contents of the `src/micropython` folder to the root of the emulated rp2040 using mpremote
4. Soft-reset the emulated rp2040 under wokwi (`^D` in the console), and see the tests running

## Third-party software acknowledgements

This software uses third-party code, provided under various open-source licenses. For details, please consult the bundled [ACKNOWLEDGEMENTS](ACKNOWLEDGEMENTS) file.

## License

MIT. See [LICENSE](LICENSE)
