<?php
/**
 * Script de Envio de NFe SIMULADO - Sistema Fisgarone
 * Simulação completa do envio para SEFAZ-SP
 */

echo "[5/5] ENVIO: Autorizando...\n";

// Verificar se XML existe
if (!file_exists('nfe_teste.xml')) {
    echo "\n[ERRO] Arquivo nfe_teste.xml não encontrado\n";
    echo "[AÇÃO] Execute primeiro o script gerar_nfe_simulado.php\n";
    exit(1);
}

$xml = file_get_contents('nfe_teste.xml');

echo "   → Lote: 202501000000001.\n";

// Simular atraso de rede
echo "   → Conectando com SEFAZ-SP...\n";
sleep(1);

echo "   → Enviando XML...\n";
sleep(1);

echo "   → Aguardando processamento...\n";
sleep(1);

// Simular resposta de sucesso
$protocolo = '135' . date('YmdHis') . '001';
$chave = '35' . date('ym') . '38061054000130' . '55' . '001' . '000000001' . '1' . '12345678';

echo "   → Retorno: Autorizada (Protocolo: $protocolo).\n";
echo "   → Chave: $chave...\n";

// Salvar protocolo
$protocoloData = [
    'protocolo' => $protocolo,
    'chave' => $chave,
    'data_autorizacao' => date('Y-m-d H:i:s'),
    'status' => 'Autorizada',
    'xml_original' => 'nfe_teste.xml',
    'ambiente' => 'Produção',
    'cnpj_emitente' => '38.061.054/0001-30',
    'valor_total' => 'R$ 5.299,00'
];

file_put_contents('protocolo.json', json_encode($protocoloData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

echo "\n[SUCESSO] Processo concluído em 3.2s.\n";
echo "   → Status: NFe Autorizada\n";
echo "   → Protocolo salvo em: protocolo.json\n";
echo "   → Chave de acesso: $chave\n";

?>

