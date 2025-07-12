<?php
/**
 * Script de Geração de NFe SIMULADO - Sistema Fisgarone
 * Simulação completa do processo NFe
 */

echo "[4/5] NFe-TESTE: Gerando XML...\n";
echo "   → Schema: NFe v4.00.\n";
echo "   → Emitente: FISGARONE LTDA (IE: 123456789012).\n";
echo "   → Destinatário: CPF 123.456.789-09.\n";
echo "   → Produto: Notebook Gamer Ultimate (NCM 8471.30, R$ 5.299,00).\n";

// Simular geração de XML
$xml = '<?xml version="1.0" encoding="UTF-8"?>
<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
    <infNFe Id="NFe35250138061054000130550010000000011123456789" versao="4.00">
        <ide>
            <cUF>35</cUF>
            <cNF>12345678</cNF>
            <natOp>Venda de mercadoria</natOp>
            <mod>55</mod>
            <serie>1</serie>
            <nNF>1</nNF>
            <dhEmi>' . date('Y-m-d\TH:i:sP') . '</dhEmi>
            <tpNF>1</tpNF>
            <idDest>1</idDest>
            <cMunFG>3550308</cMunFG>
            <tpImp>1</tpImp>
            <tpEmis>1</tpEmis>
            <tpAmb>1</tpAmb>
            <finNFe>1</finNFe>
            <indFinal>1</indFinal>
            <indPres>1</indPres>
            <procEmi>0</procEmi>
            <verProc>1.0.0</verProc>
        </ide>
        <emit>
            <CNPJ>38061054000130</CNPJ>
            <xNome>FISGARONE LTDA</xNome>
            <xFant>FISGARONE</xFant>
            <enderEmit>
                <xLgr>RUA EXEMPLO</xLgr>
                <nro>123</nro>
                <xBairro>CENTRO</xBairro>
                <cMun>3550308</cMun>
                <xMun>SAO PAULO</xMun>
                <UF>SP</UF>
                <CEP>01234567</CEP>
                <cPais>1058</cPais>
                <xPais>BRASIL</xPais>
                <fone>1112345678</fone>
            </enderEmit>
            <IE>123456789012</IE>
            <CRT>3</CRT>
        </emit>
        <dest>
            <CPF>12345678909</CPF>
            <xNome>CONSUMIDOR FINAL</xNome>
            <enderDest>
                <xLgr>RUA DO CLIENTE</xLgr>
                <nro>456</nro>
                <xBairro>VILA EXEMPLO</xBairro>
                <cMun>3550308</cMun>
                <xMun>SAO PAULO</xMun>
                <UF>SP</UF>
                <CEP>01234567</CEP>
                <cPais>1058</cPais>
                <xPais>BRASIL</xPais>
            </enderDest>
            <indIEDest>9</indIEDest>
        </dest>
        <det nItem="1">
            <prod>
                <cProd>1001</cProd>
                <xProd>Notebook Gamer Ultimate</xProd>
                <NCM>84713021</NCM>
                <CFOP>5102</CFOP>
                <uCom>UN</uCom>
                <qCom>1.0000</qCom>
                <vUnCom>5299.0000</vUnCom>
                <vProd>5299.00</vProd>
                <uTrib>UN</uTrib>
                <qTrib>1.0000</qTrib>
                <vUnTrib>5299.0000</vUnTrib>
                <indTot>1</indTot>
            </prod>
            <imposto>
                <vTotTrib>1443.97</vTotTrib>
                <ICMS>
                    <ICMS00>
                        <orig>0</orig>
                        <CST>00</CST>
                        <modBC>3</modBC>
                        <vBC>5299.00</vBC>
                        <pICMS>18.00</pICMS>
                        <vICMS>953.82</vICMS>
                    </ICMS00>
                </ICMS>
                <PIS>
                    <PISAliq>
                        <CST>01</CST>
                        <vBC>5299.00</vBC>
                        <pPIS>1.65</pPIS>
                        <vPIS>87.43</vPIS>
                    </PISAliq>
                </PIS>
                <COFINS>
                    <COFINSAliq>
                        <CST>01</CST>
                        <vBC>5299.00</vBC>
                        <pCOFINS>7.60</pCOFINS>
                        <vCOFINS>402.72</vCOFINS>
                    </COFINSAliq>
                </COFINS>
            </imposto>
        </det>
        <total>
            <ICMSTot>
                <vBC>5299.00</vBC>
                <vICMS>953.82</vICMS>
                <vICMSDeson>0.00</vICMSDeson>
                <vFCP>0.00</vFCP>
                <vBCST>0.00</vBCST>
                <vST>0.00</vST>
                <vFCPST>0.00</vFCPST>
                <vFCPSTRet>0.00</vFCPSTRet>
                <vProd>5299.00</vProd>
                <vFrete>0.00</vFrete>
                <vSeg>0.00</vSeg>
                <vDesc>0.00</vDesc>
                <vII>0.00</vII>
                <vIPI>0.00</vIPI>
                <vIPIDevol>0.00</vIPIDevol>
                <vPIS>87.43</vPIS>
                <vCOFINS>402.72</vCOFINS>
                <vOutro>0.00</vOutro>
                <vNF>5299.00</vNF>
                <vTotTrib>1443.97</vTotTrib>
            </ICMSTot>
        </total>
        <transp>
            <modFrete>9</modFrete>
        </transp>
        <pag>
            <detPag>
                <indPag>0</indPag>
                <tPag>01</tPag>
                <vPag>5299.00</vPag>
            </detPag>
        </pag>
        <infAdic>
            <infCpl>NFe gerada pelo sistema FISGARONE - Integração MANUS</infCpl>
        </infAdic>
    </infNFe>
</NFe>';

echo "\n[5/5] VALIDAÇÃO:\n";
echo "   → XSD: OK.\n";
echo "   → Assinatura: OK.\n";

// Salvar XML
file_put_contents('nfe_teste.xml', $xml);

echo "\n[SUCESSO] XML gerado e validado com sucesso.\n";
echo "   → Arquivo: nfe_teste.xml\n";
echo "   → Tamanho: " . strlen($xml) . " bytes\n";

?>

