import pandas as pd
from data_processor import PaymentDataProcessor
import io

def test_culqi_rejection():
    # Crear un CSV simulado con una transacción rechazada
    csv_content = """Empresa,Comercio,Producto,ID Venta,Marca,Nro. Tarjeta,Ult. 4 digitos,Moneda,Fecha de la transaccion,Hora de la transaccion,Nombres,Apellidos,Correo Electronico,Pais,Ciudad,Direccion,Telefono,Nombre Banco,Pais Banco,Codigo Referencia,Codigo Autorizacion,ID Terminal,Devolucion,Pre-autorizacion,Monto VENTA,Venta Final,Comision Emisor,Comision Culqi,IGV Emisor,IGV Culqi,IGV TOTAL,Comision TOTAL,Monto Aproximado Abono,ID Transaccion,Serie Terminal,Monto Propina,Estado,Codigo Respuesta,Mensaje al Comercio,Mensaje al Usuario,Modo de pago,Marca QR,Tipo de Pago,Metadata,Nro Pedido,Nro orden PE,Fecha expiracion PE,ID Comercio,Lote,Ref. Lote,Descripcion,Tipo Tokenizacion 
PEÑA LINDA,Peña Linda,CulqiFull,ID123,Visa,454775******6847,6847,PEN,2025-10-01,19:14:00,Juan,Perez,juan@email.com,PE,-,-,-,BCP,Peru,REF123,AUT123,TERM1,0,0,152.60,152.60,0,0,0,0,0,0,150.00,TRANS123,SERIE1,0,Rechazada,ERR01,Fondos insuficientes,Fondos insuficientes,CREDITO,-,Total,{},-,-,-,IDCOM,LOTE1,REF1,-,-
PEÑA LINDA,Peña Linda,CulqiFull,ID124,Visa,454775******6847,6847,PEN,2025-10-01,19:15:00,Juan,Perez,juan@email.com,PE,-,-,-,BCP,Peru,REF124,AUT124,TERM1,0,0,100.00,100.00,0,0,0,0,0,0,98.00,TRANS124,SERIE1,0,venta_exitosa,00,Aprobado,Aprobado,CREDITO,-,Total,{},-,-,-,IDCOM,LOTE1,REF1,-,-
"""
    
    processor = PaymentDataProcessor()
    
    # Simular carga de archivo
    print("Cargando datos simulados...")
    # Usar io.BytesIO para simular un archivo binario como lo espera _read_csv_robust
    file_obj = io.BytesIO(csv_content.encode('utf-8'))
    
    # Cargar datos (esto llama a _clean_culqi_data internamente)
    # Nota: load_culqi_data espera un objeto que pueda ser leído o una ruta.
    # Si pasamos un objeto file-like, _read_csv_robust intentará leerlo.
    # Pero _read_csv_robust espera 'getvalue' (Streamlit) o ruta.
    # Modificaremos para usar un archivo temporal real para ser más fieles al flujo.
    
    with open('temp_test_culqi.csv', 'w', encoding='utf-8') as f:
        f.write(csv_content)
        
    df = processor.load_culqi_data('temp_test_culqi.csv')
    
    print(f"\nTotal registros cargados: {len(df)}")
    print("Registros:")
    print(df[['Monto VENTA', 'Estado']])
    
    total = df['Monto VENTA'].sum()
    print(f"\nTotal calculado: {total}")
    
    if len(df) == 2 and total == 252.60:
        print("\nFALLO: La transacción rechazada FUE incluida.")
    elif len(df) == 1 and total == 100.00:
        print("\nÉXITO: La transacción rechazada FUE excluida.")
    else:
        print(f"\nRESULTADO INESPERADO: {len(df)} registros, Total {total}")

if __name__ == "__main__":
    test_culqi_rejection()
