[Explicación en castellano más abajo](#castellano)

English
=======================

Broquil is a Django-based management system for consumer cooperatives. It can be setup in 30 minutes on [OpenShift](http://openshift.com) thanks to the automatic installation script (free hosting!).

What is it?
-----------
The project was developed for the use of consumer cooperative El Bròquil del Gòtic, in Barcelona. Here, a group of consumers buy the produce directly from the producers, and handle the distribution of arrived products into their baskets themselves. They have around 10 producers with different characteristics:

+ Some have variable product list every week (seasonal vegetables, etc.) whereas some have the same list for a long time (milk, yogurt, etc.)
+ Some have full availability, whereas others arrive every other week or without any pre-decided schedule.
+ Some producers need to receive the total order for the cooperative ahead of time (i.e. 10 days before distribution)

This system tries to handle all these cases, and it automatizes the flow. Overall, the system has the following features:

+ Order placement system for members, which keeps track of the order history and any incidents with the orders. [Video (in Catalan)](https://vimeo.com/117320439)
+ Product distribution system for distributing the arrived products into baskets for each member. [Video (in Catalan)](https://vimeo.com/117321849)
+ Accounting module that handles the member payments, debts, quarterly fees (paid every 3 months to cover the transportation expenses), payments to the producers, etc.
+ Producer information pages.
+ Product management module where several products can be inserted at once by filling and uploading a standard format Excel file.
+ Administration panel to manage users, their permissions, the templates for all the emails sent by the system, etc.

Using all these definitions, the system gathers the products offered each week and places them in offer each Thursday. The members have time until Sunday midnight to place their orders (this is parametric and can be changed for each producer), and the products arrive on Wednesday for distribution. On Wednesday, the members responsible for the distribution use the system to prepare the baskets, and charge the members. 


Installation
--------------
To install, download [the setup script in the help/ folder](https://raw.githubusercontent.com/tiendan/broquil/generic/help/setupopenshift.sh) and follow the instructions at the top of the script. After completing the preliminary steps and filling in the required information in the script (email address, passwords, application and domain name), simply run:

    chmod +x setupopenshift.sh
    ./setupopenshift.sh

in a terminal to get your OpenShift installation up and running. Please note that the script will work only on Mac OS X and Linux systems. If at any time, the system stops to prompt you something (e.g. `Generate a token now? (yes|no)`), just enter `yes` and let it continue with the next steps.


Castellano
=======================

Broquil es un sistema de administración para cooperativas de consumo, basado en Django. Se puede configurar en 30 minutos en [OpenShift](http://openshift.com) gracias al *script* de instalación automática (alojamiento gratis!).

Qué es?
-----------
El proyecto fue desarrollado para el uso de la cooperativa de consumo El Bròquil del Gòtic, en Barcelona. Aquí, un grupo de consumidores compran los productos directamente de los productores, y se encargan de la distribución de los productos en las cestas ellas mismas. Tienen unos 10 productores con diferentes características:

+ Algunos tienen una lista de productos que varia cada semana (verduras de temporada, etc.), mientras otros tienen la misma lista para mucho tiempo (leche, yogur, etc.)
+ Algunos tienen disponibilidad cada semana, mientras otros llegan cada dos semanas o sin ningún programa predeterminado.
+ Algunos productores necesitan el pedido total de la cooperativa con más antelación (por ejemplo, 10 días antes del día de distribución)

Este sistema tiene soporte para todos estos casos, y automatiza el flujo. En general, el sistema tiene las siguientes características:

+ Sistema de hacer pedidos para el uso de las socias, con historial de pedidos y las incidencias que puedan ocurrir. [Video (en catalán)](https://vimeo.com/117320439)
+ Sistema de distribución de productos para separar los productos llegados en cestas de cada socia. [Video (en catalán)](https://vimeo.com/117321849)
+ Modulo de contabilidad para manejar los pagos y las deudas de las socias, las cuotas trimestrales (pagadas cada 3 meses para cubrir gastos de transporte), pagos a los productores, etc.
+ Páginas de información de productores.
+ Módulo de administración de productos, donde varios productos se pueden insertar al sistema a la vez rellenando y subiendo un fichero de Excel.
+ Consola de administración para administrar usuarios, sus permisos, las plantillas para todos los correos enviados por el sistema, etc.

Usando todas estas definiciones, el sistema pone los productos disponibles en la oferta cada jueves. Las socias tienen hasta domingo por la noche para hacer sus pedidos (la fecha y hora son paramétricas y se pueden cambiar para cada productor), y los productos llegan el miércoles para la distribución. El miércoles, las socias responsables de la distribución usan el sistema para preparar las cestas y cobrar a las socias. 


Instalación
--------------
Para instalar, descarga el [script de instalacion en la carpeta de help/](https://raw.githubusercontent.com/tiendan/broquil/generic/help/configuraropenshift.sh) y sigue las instrucciones al inicio del fichero. Después de completar los pasos preliminares y rellenar la información requerida (direcciones de correo, contraseñas, nombres de aplicación y dominio), simplemente ejecuta:

    chmod +x configuraropenshift.sh
    ./configuraropenshift.sh

en una consola para tener tú instalación de OpenShift configurada. Ten en cuenta que el *script* solo funcionará en sistemas de Mac OS X y Linux (Ubuntu, Debian, etc.). Si en algún momento el sistema se para y espera una respuesta (por ejemplo, `Generate a token now? (yes|no)`), simplemente entra `yes` y dejalo continuar con los pasos siguientes.