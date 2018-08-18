#!/bin/env python

import argparse
import array
import json
import os
import shutil


class Hookster:
    def __init__(self):
        self.flopp = []

    def process(self, library):
        library_name = library["library"]
        library_name_escaped = library["library_name_escaped"]

        headers = [
            "dlfcn.h",   # dlopen etc.
            "unistd.h",  # write etc.
            "stdio.h",   # printf
            "stdlib.h"   # exit
        ]

        for hook in library["hooks"]:
            if "header" in hook.keys() and hook["header"] not in headers:
                headers.append(hook["header"])

        outbuf = ""
        headers.sort()
        for header in headers:
            outbuf += "#include <{}>\n".format(header)
        outbuf += "\n"

        # Add static variables that will hold function pointers
        # to the original functions
        for hook in library["hooks"]:
            if "returns" in hook and "function" in hook and "args" in hook:
                args = hook["args"]
                args_prototype = ", ".join(
                    [["%s %s" % (b, a[b]) for b in a.keys()][0] for a in args])

                outbuf += "{} (*__{}_original)({});\n".format(
                    hook["returns"],
                    hook["function"],
                    args_prototype,
                )
        outbuf += "\n"

        for hook in library["hooks"]:
            outbuf += "int __{}_print = 1;\n".format(hook["function"],)

        library_init = ""
        for hook in library["hooks"]:
            library_init += "__{}_original = dlsym(__{}_handle, \"{}\");\n    ".format(
                hook["function"],
                library_name_escaped,
                hook["function"],
            )

        outbuf += '''
static int initialized;
static void *__%s_handle;

static void ___check_init(void) {
    if (initialized) return;

    __%s_handle = dlopen("%s", RTLD_LAZY);
    if (!__%s_handle) {
        fprintf(stderr, "%%s\\n", dlerror());
        exit(EXIT_FAILURE);
    }

    dlerror();

    %s
}
''' % (library_name_escaped, library_name_escaped, library_name, library_name_escaped, library_init)

        for hook in library["hooks"]:
            args = hook["args"]
            args_prototype = ", ".join(
                [["%s %s" % (b, a[b]) for b in a.keys()][0] for a in args])
            args_call = ", ".join(
                [[a[b] for b in a.keys()][0] for a in args])
            outbuf += '''
%s %s(%s) {
    ___check_init();
    %s ret = __%s_original(%s);
    if (__%s_print) {
        printf(\"%s\"%s);
    }
    return ret;
}
''' % (
                hook["returns"],
                hook["function"],
                args_prototype,
                hook["returns"],
                hook["function"],
                args_call,
                hook["function"],
                hook["printformat"],
                ", " + hook["printfargs"] if hook["printfargs"] else "",
            )

        c_file_path = os.path.join(
            self.outdir, "{}.c".format(library_name_escaped))

        with open(c_file_path, "w") as fp:
            fp.write(outbuf)

    def generate(self, hookfile, outdir):
        self.outdir = outdir
        with open(hookfile) as fp:
            self.hooks = json.load(fp)

        if os.path.exists(outdir):
            print("Directory '{}' exists, press enter to continue.".format(outdir))
            input()
            shutil.rmtree(outdir)

        os.makedirs(outdir)

        # TODO: Make this configurable
        architectures = [
            {
                "name": "amd64",
                "cflags": "-m64"
            },
            {
                "name": "i386",
                "cflags": "-m32"
            }
        ]

        # Generate a .c file with hooks for each library
        for library in self.hooks:
            library["library_name_escaped"] = library["library"].replace(
                ".", "_").replace("/", "_").replace("\\", "_")
            self.process(library)

        # Generate a makefile
        targets = []
        for architecture in architectures:
            for hook in self.hooks:
                targets.append("{}_{}.so".format(
                    hook["library_name_escaped"], architecture["name"]))

        outbuf = "all: {}".format(" ".join(targets))
        outbuf += "\n\n"

        for hook in self.hooks:
            for architecture in architectures:
                target_name = "{}_{}".format(
                    hook["library_name_escaped"], architecture["name"])
                outbuf += '''{}.so: {}.c
	$(CC) -c -Wall -Werror -fpic -o {}.o {} {}.c
	$(CC) -shared -o {}.so {} {}.o

'''.format(target_name, hook["library_name_escaped"], target_name,
                    architecture["cflags"], hook["library_name_escaped"],
                    target_name, architecture["cflags"], target_name)

        outbuf += '''.PHONY: clean
clean:
	rm -f *.o *.so
'''.format()

        makefile_path = os.path.join(self.outdir, "Makefile")

        with open(makefile_path, "w") as fp:
            fp.write(outbuf)


def main():
    parser = argparse.ArgumentParser(
        description="Hookster - a library hook generator")

    parser.add_argument("--hooks", default="hooks.json", metavar="file",
                        help="json with functions to hook")
    parser.add_argument("--outdir", default="out", metavar="dir",
                        help="directory where the generated files will be stored. Warning: Will remove the directory if it exists.")

    args = parser.parse_args()
    hookster = Hookster()
    hookster.generate(args.hooks, args.outdir)


if __name__ == "__main__":
    main()
