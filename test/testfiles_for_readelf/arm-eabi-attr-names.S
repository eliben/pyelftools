@ https://sourceware.org/git?p=binutils-gdb.git;a=blob;f=gas/testsuite/gas/arm/attr-names.s;h=c43fb88f67b7be158cceb13cb84caddaa7cd47b8;hb=HEAD
@ Test ARM EABI attributes, built on x86-64:
@ arm-linux-gnueabi-gcc -o arm-eabi-attr-names.o -c arm-eabi-attr-names.S
.eabi_attribute Tag_CPU_raw_name, "random-cpu"
.eabi_attribute Tag_CPU_name, "cpu"
.eabi_attribute Tag_CPU_arch, 1
.eabi_attribute Tag_CPU_arch_profile, 'S'
.eabi_attribute Tag_ARM_ISA_use, 1
.eabi_attribute Tag_THUMB_ISA_use, 1
.eabi_attribute Tag_FP_arch, 1
.eabi_attribute Tag_VFP_arch, 1
.eabi_attribute Tag_WMMX_arch, 1
.eabi_attribute Tag_Advanced_SIMD_arch, 1
.eabi_attribute Tag_PCS_config, 1
.eabi_attribute Tag_ABI_PCS_R9_use, 1
.eabi_attribute Tag_ABI_PCS_RW_data, 1
.eabi_attribute Tag_ABI_PCS_RO_data, 1
.eabi_attribute Tag_ABI_PCS_GOT_use, 1
.eabi_attribute Tag_ABI_PCS_wchar_t, 2
.eabi_attribute Tag_ABI_FP_rounding, 1
.eabi_attribute Tag_ABI_FP_denormal, 1
.eabi_attribute Tag_ABI_FP_exceptions, 1
.eabi_attribute Tag_ABI_FP_user_exceptions, 1
.eabi_attribute Tag_ABI_FP_number_model, 1
.eabi_attribute Tag_ABI_align_needed, 1
.eabi_attribute Tag_ABI_align8_needed, 1
.eabi_attribute Tag_ABI_align_preserved, 1
.eabi_attribute Tag_ABI_align8_preserved, 1
.eabi_attribute Tag_ABI_enum_size, 1
.eabi_attribute Tag_ABI_HardFP_use, 1
.eabi_attribute Tag_ABI_VFP_args, 1
.eabi_attribute Tag_ABI_WMMX_args, 1
.eabi_attribute Tag_ABI_optimization_goals, 1
.eabi_attribute Tag_ABI_FP_optimization_goals, 1
.eabi_attribute Tag_compatibility, 1, "gnu"
.eabi_attribute Tag_CPU_unaligned_access, 1
.eabi_attribute Tag_FP_HP_extension, 1
.eabi_attribute Tag_VFP_HP_extension, 1
.eabi_attribute Tag_ABI_FP_16bit_format, 1
.eabi_attribute Tag_MPextension_use, 1
.eabi_attribute Tag_DIV_use, 1
.eabi_attribute Tag_nodefaults, 0
.eabi_attribute Tag_also_compatible_with, "\06\013"
.eabi_attribute Tag_conformance, "2.08"
.eabi_attribute Tag_T2EE_use, 1
.eabi_attribute Tag_Virtualization_use, 3
