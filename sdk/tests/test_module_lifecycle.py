# SPDX-License-Identifier: GPL-3.0-or-later
"""Owner/initialized-image admission for the proposed lifecycle callback."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class LifecycleAdmission(unittest.TestCase):
    def test_exact_owner_and_initialized_bounds(self):
        source = (ROOT / 'sdk/machines/octatrack/elekloader/runtime.c').read_text()
        # Compile the actual production admission function with a fake owner
        # registry; native callback invocation belongs to the emulator tests.
        start = source.index('static int lifecycle_entry(')
        end = source.index('__attribute__((weak)) unsigned modwerk_modset_boot_restoring;', start)
        production = source[start:end]
        code = r'''
#include <assert.h>
#include <string.h>
#include "loader.h"
#include "modwerk_events.h"
static uint32_t image[32];
static unsigned known=1, initialized=64;
uint32_t modwerk_machine_reference(uint32_t value) {return value;}
int modwerk_runtime_owner_snapshot(const uint8_t *p,struct runtime_owner *o)
{
    if(!known || p!=(const uint8_t *)image)return 0;
    memset(o,0,sizeof *o);o->image_bytes=initialized;o->extent_bytes=sizeof image;return 1;
}
''' + production + r'''
int main(void)
{
    struct runtime_module m;memset(&m,0,sizeof m);
    m.dsp.image=(const uint8_t *)image;
    assert(modwerk_machine_module_admit(0));
    assert(modwerk_machine_module_admit(&m)); /* no contribution */
    uintptr_t descriptor=(uintptr_t)(image+1);
    uint32_t base=(uint32_t)(uintptr_t)image;
    m.hook[MODWERK_OT_MODULE_LIFECYCLE]=descriptor;image[1]=base+8;
    assert(modwerk_machine_module_admit(&m));
    known=0;assert(!modwerk_machine_module_admit(&m));known=1;
    const uint32_t invalid_code[]={0,base-2,base+1,base+63,base+64,base+100};
    for(unsigned i=0;i<sizeof invalid_code/sizeof *invalid_code;++i){
        image[1]=invalid_code[i];assert(!modwerk_machine_module_admit(&m));}
    image[1]=base+62;assert(modwerk_machine_module_admit(&m));
    const intptr_t invalid_record[]={-4,1,2,61,64,100};
    for(unsigned i=0;i<sizeof invalid_record/sizeof *invalid_record;++i){
        m.hook[MODWERK_OT_MODULE_LIFECYCLE]=(uintptr_t)image+invalid_record[i];
        assert(!modwerk_machine_module_admit(&m));}
    m.hook[MODWERK_OT_MODULE_LIFECYCLE]=descriptor;image[1]=base+8;
    initialized=3;assert(!modwerk_machine_module_admit(&m));
    initialized=8;assert(!modwerk_machine_module_admit(&m)); /* code is BSS */
    initialized=10;assert(modwerk_machine_module_admit(&m));
    m.dsp.image=(const uint8_t *)(image+1);assert(!modwerk_machine_module_admit(&m));
}
'''
        compiler = shutil.which('cc')
        if not compiler:
            self.skipTest('host C compiler unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / 'test.c').write_text(code)
            result = subprocess.run([compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', '-DMODWERK_RUNTIME_EVENTS',
                '-I', ROOT / 'sdk/runtime/upload', '-I', ROOT / 'sdk/runtime/loader', '-I', ROOT / 'sdk/machines/octatrack/elekloader',
                '-I', ROOT / 'sdk/machines/octatrack/include', path / 'test.c', '-o', path / 'test'],
                capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            subprocess.run([path / 'test'], check=True)


if __name__ == '__main__':
    unittest.main()
