# Documentación: Problema de Acumulación de Datos Sirvoy

## Problema Identificado

Los datos de Sirvoy se seguían acumulando en el dashboard incluso después de eliminar los archivos del uploader o al recargar la página (duplicación).

## Flujo Actual de Datos (CORREGIDO)

### 1. Carga de Archivos con Control de Duplicados

- Se ha implementado un rastreo de IDs de archivos (`st.session_state.processed_files`).
- El ID se genera combinando el nombre del archivo y su tamaño: `f"{file.name}_{file.size}"`.
- **Lógica**: Si el ID del archivo actual coincide con el último procesado, **SE OMITE EL PROCESAMIENTO**. Esto evita la duplicación al recargar la página.

### 2. Lógica de Reemplazo (Evita Acumulación)

- Cuando se detecta un archivo nuevo (ID diferente):
  1. Se carga el nuevo DataFrame.
  2. **LIMPIEZA PREVIA**: Se eliminan explícitamente los datos anteriores de ese tipo específico (Ingresos o Gastos) del DataFrame combinado (`st.session_state.sirvoy_data_combined`).
  3. **COMBINACIÓN**: Se concatenan los nuevos datos con los datos existentes del otro tipo (si los hay).
  4. Se actualiza el ID del archivo procesado.

### 3. Lógica de Eliminación Robusta

- Cuando se elimina un archivo del uploader (`file is None`):
  1. Se eliminan los datos correspondientes del DataFrame combinado.
  2. Se **RESETEA** el ID del archivo procesado a `None`. Esto permite volver a cargar el mismo archivo si el usuario lo desea.

## Solución Implementada

### 1. Inicialización de Estado

```python
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = {
        'sirvoy_file': None,
        'secured_file': None
    }
```

### 2. Procesamiento de Archivos (Ejemplo Sirvoy/Gastos)

```python
# Generar ID único
file_id = f"{sirvoy_file.name}_{sirvoy_file.size}"

# Verificar si ya fue procesado
if st.session_state.processed_files['sirvoy_file'] != file_id:
    # ... Cargar datos ...

    # LIMPIEZA: Eliminar datos anteriores de este tipo (Gastos)
    if st.session_state.sirvoy_data_combined is not None:
        st.session_state.sirvoy_data_combined = st.session_state.sirvoy_data_combined[
            st.session_state.sirvoy_data_combined['es_facturacion'] == False
        ].copy()

    # COMBINAR
    # ... concat ...

    # Actualizar ID
    st.session_state.processed_files['sirvoy_file'] = file_id
```

### 3. Validación Final

- Se mantiene la sincronización crítica antes de `unify_data()` para asegurar que el procesador tenga la versión más reciente de los datos combinados.

## Pruebas Realizadas

1. **Carga Inicial**: Correcta.
2. **Combinación**: Ingresos + Gastos se combinan correctamente.
3. **Reemplazo**: Al subir un nuevo archivo de gastos, los gastos anteriores se eliminan y se agregan los nuevos (no se suman).
4. **Recarga (Rerun)**: Al interactuar con filtros, los datos no se duplican.
5. **Eliminación**: Al quitar un archivo, los datos correspondientes desaparecen.
