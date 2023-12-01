window.showOpenFilePicker = function (options) {
    return new Promise((resolve) => {
        const input = document.createElement("input");
        input.type = "file";
        input.multiple = options.multiple;
        input.accept = options.types
            .map((type) => type.accept)
            .flatMap((inst) => Object.keys(inst).flatMap((key) => inst[key]))
            .join(",");

        input.addEventListener("change", () => {
            resolve(
                [...input.files].map((file) => {
                    return {
                        getFile: async () =>
                            new Promise((resolve) => {
                                resolve(file);
                            }),
                    };
                })
            );
        });

        input.click();
    });
}