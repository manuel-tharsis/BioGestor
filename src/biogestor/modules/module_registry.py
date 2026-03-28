from dataclasses import dataclass, field


@dataclass(frozen=True)
class MenuNode:
    key: str
    label: str
    children: list["MenuNode"] = field(default_factory=list)


MENU_TREE: list[MenuNode] = [
    MenuNode(
        key="producciones",
        label="PRODUCCIONES",
        children=[
            MenuNode(key="producciones.goma_seca", label="GOMA SECA F1620"),
            MenuNode(key="producciones.extraccion_eal", label="EXTRACCION Y EAL"),
            MenuNode(key="producciones.destilacion", label="DESTILACION"),
        ],
    ),
    MenuNode(
        key="consultas",
        label="CONSULTAS",
        children=[MenuNode(key="consultas.goma_seca_f1620", label="GOMA SECA F1620")],
    ),
    MenuNode(
        key="envios",
        label="ENVIOS",
        children=[MenuNode(key="envios.etiquetas", label="ETIQUETAS")],
    ),
    MenuNode(
        key="recepciones",
        label="RECEPCIONES",
        children=[
            MenuNode(key="recepciones.internas", label="INTERNAS"),
            MenuNode(key="recepciones.externas", label="EXTERNAS"),
        ],
    ),
    MenuNode(
        key="stock",
        label="STOCK",
        children=[
            MenuNode(
                key="stock.disolventes",
                label="DISOLVENTES",
                children=[
                    MenuNode(key="stock.disolventes.hexano", label="HEXANO"),
                    MenuNode(key="stock.disolventes.isopropanol", label="ISOPROPANOL"),
                    MenuNode(key="stock.disolventes.ciclohexano", label="CICLOHEXANO"),
                    MenuNode(
                        key="stock.disolventes.acetato_isopropilico",
                        label="ACETATO ISOPROPILICO",
                    ),
                    MenuNode(key="stock.disolventes.etanol", label="ETANOL"),
                ],
            ),
            MenuNode(key="stock.bidones", label="BIDONES DE GOMA BRUTA"),
            MenuNode(key="stock.productos", label="PRODUCTOS"),
            MenuNode(key="stock.produccion", label="PRODUCCION"),
        ],
    ),
    MenuNode(
        key="horas",
        label="HORAS TRABAJADAS",
        children=[
            MenuNode(key="horas.rg", label="REGIMEN GENERAL"),
            MenuNode(
                key="horas.ra",
                label="REGIMEN AGRARIO",
                children=[
                    MenuNode(key="horas.ra.tractoristas", label="TRACTORISTAS"),
                    MenuNode(key="horas.ra.cuadrillas", label="CUADRILLAS"),
                ],
            ),
        ],
    ),
]
