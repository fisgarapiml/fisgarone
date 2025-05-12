$(document).ready(function() {
    // Carrega o menu dinâmico
    $.getJSON("{{ url_for('bp_home.get_menu') }}", function(menuData) {
        const $menuContainer = $('.menu');
        $menuContainer.empty();

        menuData.forEach(function(group) {
            // Cria grupo do menu
            const $group = $(`
                <div class="menu-group">
                    <div class="menu-group-title">${group.titulo}</div>
                    <ul class="menu-items"></ul>
                </div>
            `);

            // Adiciona itens
            group.itens.forEach(function(item) {
                const hasSubmenu = item.submenu && item.submenu.length > 0;

                const $item = $(`
                    <li class="menu-item ${hasSubmenu ? 'has-submenu' : ''}">
                        <a href="${hasSubmenu ? '#' : item.url}" class="menu-link">
                            <i class="${item.icone}"></i>
                            <span class="menu-text">${item.nome}</span>
                            ${hasSubmenu ? '<i class="fas fa-chevron-down dropdown-icon"></i>' : ''}
                        </a>
                        ${hasSubmenu ? `
                        <ul class="submenu">
                            ${item.submenu.map(subItem => `
                                <li class="submenu-item">
                                    <a href="${subItem.url}">${subItem.nome}</a>
                                </li>
                            `).join('')}
                        </ul>
                        ` : ''}
                    </li>
                `);

                $group.find('.menu-items').append($item);
            });

            $menuContainer.append($group);
        });

        // Configura interações do menu
        setupMenuInteractions();
    }).fail(function(error) {
        console.error("Erro ao carregar menu:", error);
        // Fallback básico
        $('.menu').html(`
            <div class="menu-group">
                <div class="menu-group-title">Menu</div>
                <ul class="menu-items">
                    <li class="menu-item">
                        <a href="{{ url_for('bp_home.index') }}" class="menu-link">
                            <i class="fas fa-home"></i>
                            <span>Home</span>
                        </a>
                    </li>
                </ul>
            </div>
        `);
    });

    function setupMenuInteractions() {
        // Submenus
        $(document).on('click', '.menu-item.has-submenu > .menu-link', function(e) {
            e.preventDefault();
            const $parentItem = $(this).parent();
            const $submenu = $parentItem.find('.submenu');

            // Fecha outros submenus
            $('.submenu').not($submenu).removeClass('show');
            $('.menu-item.has-submenu').not($parentItem).removeClass('active');

            // Alterna o submenu atual
            $submenu.toggleClass('show');
            $parentItem.toggleClass('active');
        });

        // Marca item ativo
        const currentPath = window.location.pathname;
        $('.menu-link').each(function() {
            if ($(this).attr('href') === currentPath) {
                $(this).addClass('active');

                // Abre o submenu pai se existir
                const $submenu = $(this).closest('.menu-item').find('.submenu');
                if ($submenu.length) {
                    $submenu.addClass('show');
                    $(this).closest('.menu-item').addClass('active');
                }
            }
        });

        // Efeito hover
        $(document)
            .on('mouseenter', '.menu-item', function() {
                $(this).css('box-shadow', '0 0 10px rgba(0, 136, 255, 0.3)');
            })
            .on('mouseleave', '.menu-item', function() {
                $(this).css('box-shadow', 'none');
            });
    }
});