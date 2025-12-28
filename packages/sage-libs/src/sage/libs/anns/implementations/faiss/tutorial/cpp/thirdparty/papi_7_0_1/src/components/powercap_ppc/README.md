# POWERCAP_PPC Component

The POWERCAP_PPC component supports measuring and capping power usage on recent IBM PowerPC
architectures (Power9 and later) using the powercap interface exposed through the Linux kernel.

- [Enabling the POWERCAP_PPC Component](#markdown-header-enabling-the-powercap-ppc-component)
- [Known Limitations](#markdown-header-known-limitations)
- [FAQ](#markdown-header-faq)

______________________________________________________________________

## Enabling the POWERCAP_PPC Component

To enable reading of POWERCAP_PPC counters the user needs to link against a PAPI library that was
configured with the POWERCAP_PPC component enabled. As an example the following command:
`./configure --with-components="powercap_ppc"` is sufficient to enable the component.

Typically, the utility `papi_components_avail` (available in `papi/src/utils/papi_components_avail`)
will display the components available to the user, and whether they are disabled, and when they are
disabled why.

## Known Limitations

The actions described below will generally require superuser ability. Note, these actions may have
security and performance consequences, so please make sure you know what you are doing.

Use chmod to set site-appropriate access permissions (e.g. 444) for
/sys/firmware/opal/powercap/powercap-(min|max)

Use chmod to set site-appropriate access permissions (e.g. 664) for
/sys/firmware/opal/powercap/powercap-current

## FAQ

1. [Measuring and Capping Power](#markdown-header-measuring-and-capping-power)

## Measuring and Capping Power

The powercap sysfs interface exposes power measurments as R/W regsiter-like power settings. The
counters and R/W settings apply to the Power9.

These counters and settings are exposed though this PAPI component and can be accessed just like any
normal PAPI counter. Running the "powercap_basic" test in the test directory will list all the
events on a system. There is also a "powercap_limit" test in the test directory that shows how a
power limit is applied.

Note: Power Limiting using powercap_ppc **does not** require root privileges. Write permission to
the file /sys/firmware/opal/powercap/powercap-current is "enough".
