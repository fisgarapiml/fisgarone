$(document).ready(function() {
    // Carrega o menu dinâmico
    //$.get('/api/menu', function(menu) {
        //const $menu = $('.sidebar .menu');

        menu.forEach(category => {
            // Adiciona categoria
            //$menu.append(`<div class="menu-category">${category.titulo}</div>`);

            // Adiciona itens
            //category.itens.forEach(item => {
                $menu.append(`
                    <a href="${item.url}" class="menu-item">
                        <i class="${item.icone}"></i>
                        <span>${item.nome}</span>
                        ${item.badge ? `<span class="badge">${item.badge}</span>` : ''}
                    </a>
                `);
            });
        });

        // Marca item ativo
        //const currentPath = window.location.pathname;
        $('.menu-item').each(function() {
            if ($(this).attr('href') === currentPath) {
                $(this).addClass('active');
            }
        });
    });

    // Efeitos neon nos itens ativos
   // $(document).on('mouseenter', '.menu-item', function() {
        $(this).css('box-shadow', '0 0 10px rgba(0, 136, 255, 0.3)');
    }).on('mouseleave', '.menu-item', function() {
        $(this).css('box-shadow', 'none');
    });
});

//document.addEventListener('DOMContentLoaded', function() {
    //fetch('/api/menu')
        .then(response => response.json())
        .then(menu => {
            const menuContainer = document.querySelector('.sidebar .menu');
            menuContainer.innerHTML = '';

            menu.forEach(category => {
                // Adiciona categoria
                const categoryElement = document.createElement('div');
                categoryElement.className = 'menu-category';
                categoryElement.textContent = category.titulo;
                menuContainer.appendChild(categoryElement);

                // Adiciona itens
                //category.itens.forEach(item => {
                    const itemElement = document.createElement('a');
                    itemElement.href = item.url;
                    itemElement.className = 'menu-item';
                    itemElement.innerHTML = `
                        <i class="${item.icone}"></i>
                        <span>${item.nome}</span>
                    `;
                    menuContainer.appendChild(itemElement);

                    // Marca item ativo
                    if (item.url === window.location.pathname) {
                        itemElement.classList.add('active');
                    }
                });
            });
        })
        //.catch(error => console.error('Erro ao carregar menu:', error));
});