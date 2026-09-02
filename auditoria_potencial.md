# Auditoría de distribución de potencial — Speedster

Fecha de revisión: 2 de septiembre de 2026.

## Conclusión

La clasificación oficial se calcula sobre el puntaje decimal original, sin
redondeo previo:

- 0 a 79,99: Potencial bajo.
- 80 a 84,99: Potencial medio.
- 85 a 100: Alto potencial.

Con el archivo actualizado hay 33 registros en la hoja Potencial, de los cuales
32 tienen puntaje. La distribución es 3 personas en Potencial bajo, 2 en
Potencial medio y 27 en Alto potencial.

## Fuente controlante

- Archivo: `Fase_I_Evaluación_360__180__90__copia_.xlsx`.
- Hoja: `Potencial`.
- Campo: `COMPETENCIAS`, normalizado como `evaluacion_potencial`.
- Registros con puntaje: 32.
- Promedio: 91,8681.
- Rango observado: 65,21 a 100,00.

## Caso de borde validado

Mendoza Coste Indhira Severiana tiene 79,91. Ese valor permanece por debajo de
80,00 y se clasifica como **Potencial bajo**. Las etiquetas escritas en el
archivo de origen no prevalecen sobre el puntaje numérico: dashboard, carga a
Neon y reportes recalculan la categoría con la misma regla.
