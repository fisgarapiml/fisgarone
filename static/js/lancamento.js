$(document).ready(function() {
  // Configura todos os selects dinâmicos
  $('.select-dinamico').select2({
    tags: true,
    placeholder: "Selecione ou digite para criar",
    width: '100%'
  }).on('select2:select', function(e) {
    if (e.params.data.tag) {
      const campo = $(this).data('campo');
      const valor = e.params.data.text;

      fetch('/api/adicionar_opcao', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ campo, valor })
      }).then(r => r.json()).then(data => {
        if (!data.success) {
          console.error("Erro ao salvar:", data.error);
          $(this).val(null).trigger('change');
        }
      });
    }
  });

  // Formata data para o padrão do seu DB (DD/MM/YYYY)
  $('input[type="date"]').on('change', function() {
    const date = new Date(this.value);
    if (!isNaN(date.getTime())) {
      const day = date.getDate().toString().padStart(2, '0');
      const month = (date.getMonth() + 1).toString().padStart(2, '0');
      this.value = `${day}/${month}/${date.getFullYear()}`;
    }
  });

  // Atualiza status quando valor pago ou vencimento mudar
  $('input[name="valor_pago"], input[name="vencimento"]').on('change', function() {
    const valorPago = $('input[name="valor_pago"]').val();
    const vencimento = $('input[name="vencimento"]').val();

    if (valorPago && parseFloat(valorPago) > 0) {
      $('select[name="status"]').val('paid').trigger('change');
    } else if (vencimento) {
      const [day, month, year] = vencimento.split('/');
      const vencDate = new Date(year, month - 1, day);
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      if (vencDate < today) {
        $('select[name="status"]').val('overdue').trigger('change');
      } else {
        $('select[name="status"]').val('pending').trigger('change');
      }
    }
  });
});