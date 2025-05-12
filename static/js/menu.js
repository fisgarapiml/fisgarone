document.addEventListener("DOMContentLoaded", function () {
    fetch("/api/menu")
        .then(res => res.json())
        .then(data => {
            const menu = document.getElementById("main-menu");
            data.forEach(group => {
                group.itens.forEach(item => {
                    const link = document.createElement("a");
                    link.href = item.url;
                    link.className = "menu-item";
                    link.innerHTML = `<i class="${item.icone}"></i><span>${item.nome}</span>`;

                    // Ativo se URL bate
                    if (window.location.pathname === new URL(item.url, window.location.origin).pathname) {
                        link.classList.add("active");
                    }

                    menu.appendChild(link);
                });
            });
        });

    // Tema salvo no localStorage
    const theme = localStorage.getItem("theme") || "dark";
    if (theme === "dark") {
        document.body.classList.add("dark-theme");
        document.getElementById("dark-mode").classList.add("active");
    } else {
        document.body.classList.remove("dark-theme");
        document.getElementById("light-mode").classList.add("active");
    }

    // Botões de troca
    document.getElementById("dark-mode").addEventListener("click", () => {
        document.body.classList.add("dark-theme");
        localStorage.setItem("theme", "dark");
        document.getElementById("dark-mode").classList.add("active");
        document.getElementById("light-mode").classList.remove("active");
    });

    document.getElementById("light-mode").addEventListener("click", () => {
        document.body.classList.remove("dark-theme");
        localStorage.setItem("theme", "light");
        document.getElementById("light-mode").classList.add("active");
        document.getElementById("dark-mode").classList.remove("active");
    });
});
