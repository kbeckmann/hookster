# Hookster - a library hook generator

This tool generates hook libraries that you can use to hook library functions such as strlen() etc. You can use this to modify or dump whatever passes through the function.

## Usage:
A JSON file specifies which functions to hook. Here is an example where `char * strcat(dest, src)` is hooked:
```
[
    {
        "library": "libc.so.6",
        "hooks": [
            {
                "function": "strcat",
                "returns": "char *",
                "args": [
                    {
                        "char *": "dest"
                    },
                    {
                        "const char *": "src"
                    }
                ],
                "header": "string.h",
                "printformat": "strcat({%s}, {%s})",
                "printfargs": "dest, src"
            }, ...
        ]
    }, ...
]
```

See [hooks.json](./hooks.json) a more complete example.

The tool is invoked by running:
```
# 1. Run the tool in order to generate c-files and a Makefile in out/
python3 hookster.py --hooks hooks.json --outdir out

# 2. Build the libraries
cd out
make

# 3. You may then preload the library and run your executable.
#    Note that you might have to preload /usr/lib/libdl.so in order
#    to have access to dlopen/dlsym.
#    Here we are using the generated libc hook and execute `ls`:
LD_PRELOAD=./libc_so_6_amd64.so:/usr/lib/libdl.so ls

strlen({tty}) = 3
...

```
