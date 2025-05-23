// Classe principal do Painel NF-e
class NFePanel {
  constructor() {
    this.products = [];
    this.selectedProducts = new Set();
    this.filters = {
      status: 'all',
      supplier: 'all'
    };

    this.initElements();
    this.initEvents();
    this.loadProducts();
  }

  initElements() {
    // Elementos da UI
    this.elements = {
      productsList: document.getElementById('products-list'),
      statusFilter: document.getElementById('status-filter'),
      supplierFilter: document.getElementById('supplier-filter'),
      expandAllBtn: document.getElementById('expand-all'),
      approveAllBtn: document.getElementById('approve-all'),
      confirmImportBtn: document.getElementById('confirm-import'),
      selectedCount: document.getElementById('selected-count'),
      totalItems: document.getElementById('total-items'),
      modal: document.getElementById('detail-modal'),
      closeModalBtns: document.querySelectorAll('.close-modal, .close-modal-btn'),
      modalContent: document.getElementById('modal-product-details')
    };

    // Contadores
    this.counters = {
      total: document.getElementById('total-count'),
      new: document.getElementById('new-count'),
      updated: document.getElementById('updated-count'),
      priceChange: document.getElementById('price-change-count'),
      unchanged: document.getElementById('unchanged-count')
    };
  }

  initEvents() {
    // Filtros
    this.elements.statusFilter.addEventListener('change', (e) => {
      this.filters.status = e.target.value;
      this.renderProducts();
    });

    this.elements.supplierFilter.addEventListener('change', (e) => {
      this.filters.supplier = e.target.value;
      this.renderProducts();
    });

    // Ações
    this.elements.expandAllBtn.addEventListener('click', () => this.toggleExpandAll());
    this.elements.approveAllBtn.addEventListener('click', () => this.approveAll());
    this.elements.confirmImportBtn.addEventListener('click', () => this.confirmImport());

    // Modal
    this.elements.closeModalBtns.forEach(btn => {
      btn.addEventListener('click', () => this.closeModal());
    });

    // Fechar modal ao clicar fora
    window.addEventListener('click', (e) => {
      if (e.target === this.elements.modal) {
        this.closeModal();
      }
    });
  }

  async loadProducts() {
    try {
      // Simulação de carregamento - na prática seria uma chamada AJAX
      const response = await fetch('/api/nfe/import');
      this.products = await response.json();

      this.updateCounters();
      this.updateSupplierFilter();
      this.renderProducts();
    } catch (error) {
      console.error('Erro ao carregar produtos:', error);
      this.showNotification('Erro ao carregar produtos da NF-e', 'error');
    }
  }

  updateCounters() {
    const counts = {
      total: this.products.length,
      new: this.products.filter(p => p.status === 'new').length,
      updated: this.products.filter(p => p.status === 'updated').length,
      priceChange: this.products.filter(p => p.status === 'price-change').length,
      unchanged: this.products.filter(p => p.status === 'unchanged').length
    };

    // Atualiza os contadores na UI
    for (const [key, value] of Object.entries(counts)) {
      this.counters[key].textContent = value;
    }

    // Atualiza contagem total no footer
    this.elements.totalItems.textContent = counts.total;
  }

  updateSupplierFilter() {
    const suppliers = [...new Set(this.products.map(p => p.supplier))];
    const filter = this.elements.supplierFilter;

    // Limpa opções existentes (mantendo a primeira)
    while (filter.options.length > 1) {
      filter.remove(1);
    }

    // Adiciona novos fornecedores
    suppliers.forEach(supplier => {
      const option = document.createElement('option');
      option.value = supplier;
      option.textContent = supplier;
      filter.appendChild(option);
    });
  }

  renderProducts() {
    const filteredProducts = this.products.filter(product => {
      // Filtro por status
      if (this.filters.status !== 'all' && product.status !== this.filters.status) {
        return false;
      }

      // Filtro por fornecedor
      if (this.filters.supplier !== 'all' && product.supplier !== this.filters.supplier) {
        return false;
      }

      return true;
    });

    // Gera HTML para cada produto
    this.elements.productsList.innerHTML = filteredProducts
      .map(product => this.generateProductHTML(product))
      .join('');

    // Adiciona eventos aos produtos renderizados
    this.addProductEvents();
  }

  generateProductHTML(product) {
    const isSelected = this.selectedProducts.has(product.id);

    return `
      <div class="product-item ${product.status} ${isSelected ? 'selected' : ''}" data-id="${product.id}">
        <div class="product-header">
          <div class="product-title">
            <input type="checkbox" class="product-checkbox" ${isSelected ? 'checked' : ''}>
            <span>${product.name}</span>
          </div>
          <div class="product-status ${product.status}">
            ${this.getStatusLabel(product.status)}
          </div>
        </div>

        <div class="product-body">
          <div class="field-comparison">
            <div class="field-group">
              <span class="field-label">Código</span>
              <div class="field-value ${product.changes.code ? 'changed' : ''}">
                ${product.code}
              </div>
            </div>

            ${product.oldValues?.code ? `
            <div class="field-group">
              <span class="field-label">Código Anterior</span>
              <div class="field-value">
                ${product.oldValues.code}
              </div>
            </div>
            ` : '<div></div>'}
          </div>

          <!-- Demais campos comparativos -->

          <div class="product-actions">
            <button class="btn btn-secondary btn-view-details" data-id="${product.id}">
              <i class="fas fa-search"></i> Detalhes
            </button>
            <button class="btn btn-primary btn-approve" data-id="${product.id}">
              <i class="fas fa-check"></i> Aprovar
            </button>
          </div>
        </div>
      </div>
    `;
  }

  getStatusLabel(status) {
    const labels = {
      'new': 'Novo',
      'updated': 'Atualizado',
      'price-change': 'Custo Alterado',
      'unchanged': 'Sem Alteração'
    };
    return labels[status] || status;
  }

  addProductEvents() {
    // Evento de clique no cabeçalho para expandir/recolher
    document.querySelectorAll('.product-header').forEach(header => {
      header.addEventListener('click', (e) => {
        // Não dispara se o clique foi em um filho que já tem seu próprio evento
        if (e.target.tagName === 'INPUT' || e.target.closest('button')) {
          return;
        }

        const productItem = header.closest('.product-item');
        productItem.classList.toggle('expanded');
      });
    });

    // Checkbox de seleção
    document.querySelectorAll('.product-checkbox').forEach(checkbox => {
      checkbox.addEventListener('change', (e) => {
        const productId = e.target.closest('.product-item').dataset.id;

        if (e.target.checked) {
          this.selectedProducts.add(productId);
        } else {
          this.selectedProducts.delete(productId);
        }

        this.updateSelectionUI();
      });
    });

    // Botão de detalhes
    document.querySelectorAll('.btn-view-details').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const productId = e.target.closest('button').dataset.id;
        this.showProductDetails(productId);
      });
    });

    // Botão de aprovar
    document.querySelectorAll('.btn-approve').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const productId = e.target.closest('button').dataset.id;
        this.approveProduct(productId);
      });
    });
  }

  updateSelectionUI() {
    // Atualiza contagem no footer
    this.elements.selectedCount.textContent = this.selectedProducts.size;

    // Habilita/desabilita botão de confirmação
    this.elements.confirmImportBtn.disabled = this.selectedProducts.size === 0;

    // Atualiza visual dos itens selecionados
    document.querySelectorAll('.product-item').forEach(item => {
      const isSelected = this.selectedProducts.has(item.dataset.id);
      item.classList.toggle('selected', isSelected);
    });
  }

  toggleExpandAll() {
    const allExpanded = [...document.querySelectorAll('.product-item')]
      .every(item => item.classList.contains('expanded'));

    document.querySelectorAll('.product-item').forEach(item => {
      if (allExpanded) {
        item.classList.remove('expanded');
      } else {
        item.classList.add('expanded');
      }
    });

    // Atualiza texto do botão
    this.elements.expandAllBtn.innerHTML = allExpanded
      ? '<i class="fas fa-expand"></i> Expandir Tudo'
      : '<i class="fas fa-compress"></i> Recolher Tudo';
  }

  approveAll() {
    const visibleProducts = [...document.querySelectorAll('.product-item:not([style*="display: none"])']
      .map(item => item.dataset.id);

    visibleProducts.forEach(id => this.selectedProducts.add(id));
    this.updateSelectionUI();
    this.showNotification(`${visibleProducts.length} itens selecionados para aprovação`);
  }

  approveProduct(productId) {
    this.selectedProducts.add(productId);
    this.updateSelectionUI();

    // Marca visualmente como aprovado
    const productItem = document.querySelector(`.product-item[data-id="${productId}"]`);
    productItem.classList.add('approved');

    this.showNotification('Item aprovado com sucesso');
  }

  async confirmImport() {
    if (this.selectedProducts.size === 0) return;

    if (!confirm(`Deseja confirmar a importação de ${this.selectedProducts.size} itens?`)) {
      return;
    }

    try {
      this.elements.confirmImportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';
      this.elements.confirmImportBtn.disabled = true;

      // Simulação de envio para o servidor
      const response = await fetch('/api/nfe/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          productIds: [...this.selectedProducts]
        })
      });

      const result = await response.json();

      if (result.success) {
        this.showNotification('Importação confirmada com sucesso!', 'success');

        // Remove os itens confirmados da lista
        this.products = this.products.filter(p => !this.selectedProducts.has(p.id));
        this.selectedProducts.clear();

        // Atualiza UI
        this.updateCounters();
        this.renderProducts();
        this.updateSelectionUI();
      } else {
        throw new Error(result.message || 'Erro ao confirmar importação');
      }
    } catch (error) {
      console.error('Erro ao confirmar importação:', error);
      this.showNotification(error.message, 'error');
    } finally {
      this.elements.confirmImportBtn.innerHTML = '<i class="fas fa-file-import"></i> Confirmar Importação';
      this.elements.confirmImportBtn.disabled = false;
    }
  }

  showProductDetails(productId) {
    const product = this.products.find(p => p.id === productId);
    if (!product) return;

    // Preenche o modal com os detalhes do produto
    this.elements.modalContent.innerHTML = `
      <div class="product-details">
        <h4>${product.name}</h4>
        <p class="supplier">Fornecedor: ${product.supplier}</p>

        <div class="detail-section">
          <h5>Informações Principais</h5>
          <div class="detail-grid">
            ${this.generateDetailRow('Código', product.code, product.oldValues?.code)}
            ${this.generateDetailRow('Descrição', product.description, product.oldValues?.description)}
            ${this.generateDetailRow('Unidade', product.unit, product.oldValues?.unit)}
          </div>
        </div>

        <div class="detail-section">
          <h5>Valores</h5>
          <div class="detail-grid">
            ${this.generateDetailRow('Preço Unitário', product.unitPrice, product.oldValues?.unitPrice, true)}
            ${this.generateDetailRow('IPI', product.ipi, product.oldValues?.ipi, true)}
            ${this.generateDetailRow('Preço Final', product.finalPrice, product.oldValues?.finalPrice, true)}
          </div>
        </div>

        <div class="notes">
          <label>Observações:</label>
          <textarea class="notes-input" placeholder="Adicione observações se necessário...">${product.notes || ''}</textarea>
        </div>
      </div>
    `;

    this.openModal();
  }

  generateDetailRow(label, currentValue, oldValue, isCurrency = false) {
    const hasChanged = oldValue !== undefined && currentValue !== oldValue;

    const formatValue = (value) => {
      if (value === undefined || value === null) return '-';
      return isCurrency
        ? `R$ ${parseFloat(value).toFixed(2).replace('.', ',')}`
        : value;
    };

    return `
      <div class="detail-row ${hasChanged ? 'changed' : ''}">
        <span class="detail-label">${label}:</span>
        <span class="detail-value">${formatValue(currentValue)}</span>
        ${hasChanged ? `
          <span class="detail-old-value">
            <i class="fas fa-arrow-right"></i> ${formatValue(oldValue)}
          </span>
        ` : ''}
      </div>
    `;
  }

  openModal() {
    this.elements.modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  closeModal() {
    this.elements.modal.style.display = 'none';
    document.body.style.overflow = '';
  }

  showNotification(message, type = 'success') {
    // Implementação de notificação (pode usar biblioteca ou custom)
    console.log(`[${type}] ${message}`);
  }
}

// Inicializa o painel quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
  new NFePanel();
});