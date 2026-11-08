import shutil

F = 'inventario_mercancia.py'   # <- nombre real de tu archivo
shutil.copy(F, F + '.bak')
s = open(F, encoding='utf-8').read()

def st(nombre, old, new):
    global s
    k = s.count(old)
    if k == 1:
        s = s.replace(old, new)
    print(nombre, 'OK' if k == 1 else f'NO ENCONTRADO ({k})')

# 1) Umbral de alerta: 30 kg
st('umbral', "LIMITE_KG_ALERTA = 50.0", "LIMITE_KG_ALERTA = 30.0")

# 2) Aviso en la carga manual: decimales con valor >= 10 (30.000 se lee como gramos)
st('ambiguo',
   '        avisos.append("Un valor entre 10 y 99 se toma como GRAMOS")\n',
   '        avisos.append("Un valor entre 10 y 99 se toma como GRAMOS")\n'
   '    if any(n >= 10 and not float(n).is_integer() for n in nums):\n'
   '        avisos.append("Número con decimales mayor a 10: se lee como GRAMOS (30.000 = 0.03 kg). ¿Querías 30 kg?")\n')

# 3) Confirmación antes de iniciar la carga en Java
st('aviso_carga',
   "        # 4) Confirmación con resumen\n",
   '''        grandes = self.df_consolidado[self.df_consolidado['Cantidad_Num'] > LIMITE_KG_ALERTA]
        if not grandes.empty:
            detalle = "\\n".join(
                f"• {r['Producto_Original']}: {r['Cantidad_Num']:.3f} kg  (anotado: {r.get('Cantidad_Original', '')})"
                for _, r in grandes.head(10).iterrows())
            if not messagebox.askyesno(
                    "⚠ Cantidades muy altas",
                    f"Estos artículos superan {LIMITE_KG_ALERTA:.0f} kg:\\n\\n{detalle}\\n\\n"
                    "¿Seguro que no es un error de dedo?\\n\\n"
                    "SÍ = continuar · NO = revisar", icon="warning"):
                return

        # 4) Confirmación con resumen
''')

# 4) Autoscroll de la vista previa en la carga manual
st('autoscroll',
   '                fg="#C62828" if e else ("#B26A00" if w else "#2E7D32"))\n',
   '''                fg="#C62828" if e else ("#B26A00" if w else "#2E7D32"))
            hijos = tv.get_children()
            if hijos:
                lineas_txt = int(txt.index("end-1c").split(".")[0])
                cursor_linea = int(txt.index("insert").split(".")[0])
                if cursor_linea >= lineas_txt - 1:
                    tv.see(hijos[-1])
                elif str(cursor_linea) in hijos:
                    tv.see(str(cursor_linea))
''')

open(F, 'w', encoding='utf-8').write(s)