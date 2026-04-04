# Etapa de construcción de ejemplos: documentos tipo para LLM

Este documento define una etapa explícita para construir ejemplos de entrada/salida para tareas con LLM orientadas a extracción, clasificación y normalización de documentos.

## Objetivo de la etapa

Tener un set base de **8 documentos tipo** que permita:

- Probar prompts y reglas de extracción.
- Evaluar cobertura de campos obligatorios.
- Detectar ambigüedades entre formatos reales.
- Estandarizar criterios de calidad antes de pasar a producción.

## Etapa propuesta: “Construcción de ejemplos”

1. **Definir esquema por tipo documental**  
   Campos esperados, opcionales y reglas de validación.
2. **Redactar plantilla textual canónica**  
   Describir estructura, secciones y metadatos típicos.
3. **Generar variantes realistas**  
   Diferentes formatos, orden de secciones, abreviaturas y ruido.
4. **Anotar ground truth**  
   JSON esperado por documento con campos normalizados.
5. **Validar con LLM**  
   Ejecutar extracción y comparar contra ground truth.
6. **Cerrar brechas**  
   Ajustar prompt, diccionario y post-procesamiento.

---

## 8 casos de ejemplo (documentos tipo)

## 1) Cédula de identidad

**Cómo es:**  
Documento oficial de identificación personal, usualmente con foto, nombres, apellidos, número único, fecha de nacimiento, nacionalidad, sexo, fecha de emisión/vencimiento y entidad emisora.

**Campos recomendados para extracción:**
- `tipo_documento`
- `numero_documento`
- `nombres`
- `apellidos`
- `fecha_nacimiento`
- `nacionalidad`
- `sexo`
- `fecha_emision`
- `fecha_vencimiento`
- `entidad_emisora`

## 2) Certificado de título

**Cómo es:**  
Constancia académica emitida por institución de educación superior que acredita grado o título obtenido, con datos del titular, programa, fecha de otorgamiento, autoridad firmante y folio/código de verificación.

**Campos recomendados para extracción:**
- `tipo_documento`
- `titular_nombre_completo`
- `titulo_otorgado`
- `institucion`
- `fecha_otorgamiento`
- `modalidad` (si existe)
- `folio_o_codigo`
- `autoridad_firmante`

## 3) Curriculum vitae (CV)

**Cómo es:**  
Resumen profesional estructurado por secciones: datos personales, perfil, experiencia, formación, habilidades, certificaciones, idiomas y referencias.

**Campos recomendados para extracción:**
- `tipo_documento`
- `nombre_completo`
- `email`
- `telefono`
- `perfil_profesional`
- `experiencia_laboral[]`
- `formacion_academica[]`
- `habilidades[]`
- `idiomas[]`
- `certificaciones[]`

## 4) Programa de estudios (syllabus)

**Cómo es:**  
Documento académico de asignatura con identificación del curso, competencias, unidades temáticas, metodología, bibliografía, sistema de evaluación y cronograma.

**Campos recomendados para extracción:**
- `tipo_documento`
- `asignatura`
- `codigo_asignatura`
- `creditos`
- `docente`
- `competencias[]`
- `unidades[]`
- `metodologia`
- `evaluacion`
- `bibliografia[]`

## 5) Licencia de conducir

**Cómo es:**  
Documento oficial que habilita conducción, con número de licencia, clase/categoría, identificación del titular, fechas de emisión y expiración, restricciones y autoridad emisora.

**Campos recomendados para extracción:**
- `tipo_documento`
- `numero_licencia`
- `nombre_titular`
- `categoria`
- `fecha_emision`
- `fecha_expiracion`
- `restricciones`
- `entidad_emisora`

## 6) Certificado de nacimiento

**Cómo es:**  
Acta/certificado registral que acredita nacimiento, incluyendo datos del inscrito, fecha/lugar de nacimiento, datos parentales, número de acta, oficialía y fecha de inscripción.

**Campos recomendados para extracción:**
- `tipo_documento`
- `nombre_inscrito`
- `fecha_nacimiento`
- `lugar_nacimiento`
- `nombre_madre`
- `nombre_padre`
- `numero_acta`
- `oficialia`
- `fecha_inscripcion`

## 7) Certificado de notas / concentración de calificaciones

**Cómo es:**  
Documento emitido por institución educativa con listado de asignaturas, periodos, calificaciones, promedio y estado académico.

**Campos recomendados para extracción:**
- `tipo_documento`
- `estudiante_nombre`
- `institucion`
- `programa`
- `periodo`
- `asignaturas[]`
- `promedio_general`
- `estado_academico`
- `fecha_emision`

## 8) Contrato de trabajo

**Cómo es:**  
Documento legal entre empleador y trabajador con datos de partes, cargo, jornada, remuneración, vigencia, cláusulas y firmas.

**Campos recomendados para extracción:**
- `tipo_documento`
- `empleador`
- `trabajador`
- `cargo`
- `fecha_inicio`
- `fecha_termino` (si aplica)
- `jornada`
- `remuneracion`
- `clausulas_relevantes[]`
- `firmas`

---

## Criterios mínimos de calidad para los ejemplos

- Al menos 3 variantes por tipo documental (limpio, ruido OCR, formato alternativo).
- Cobertura de campos obligatorios ≥ 95%.
- Fechas normalizadas a formato ISO (`YYYY-MM-DD`) cuando sea posible.
- Trazabilidad: cada ejemplo debe tener `id_ejemplo`, `version_prompt` y `resultado_esperado`.
