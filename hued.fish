# hued — set terminal colors based on nearest .hued file
#
# Place this file in ~/.config/fish/conf.d/

set -g _HUED_DIR (status dirname)

function _hued_apply_channel --argument-names osc reset_osc value
    set value (string trim "$value" | string lower)
    if test -z "$value" -o "$value" = none
        printf "\e]%s;\a" $reset_osc
        return
    end
    set hex (string replace '#' '' -- "$value")
    if not string match -qr '^[0-9a-f]{6}$' -- "$hex"
        set hit (grep -m1 "\[$hex\]=" "$_HUED_DIR/hued-names.sh" 2>/dev/null | cut -d= -f2)
        set hex (string replace '#' '' -- "$hit")
    end
    if string match -qr '^[0-9a-f]{6}$' -- "$hex"
        printf "\e]%s;rgb:%s/%s/%s\a" $osc \
            (string sub -s 1 -l 2 $hex) \
            (string sub -s 3 -l 2 $hex) \
            (string sub -s 5 -l 2 $hex)
    end
end

function _hued_on_sigusr1 --on-signal SIGUSR1
    _hued_apply
end

function _hued_apply --on-event fish_prompt
    set bg ""
    set fg ""

    set dir $PWD
    while test "$dir" != /
        if test -f "$dir/.hued"
            set bg (grep -m1 '^background=' "$dir/.hued" | cut -d= -f2)
            set fg (grep -m1 '^foreground=' "$dir/.hued" | cut -d= -f2)
            if test -n "$bg" -o -n "$fg"
                break
            end
        end
        set dir (dirname $dir)
    end

    if set -q HUED_BACKGROUND; and test -n "$HUED_BACKGROUND"
        set bg $HUED_BACKGROUND
    end
    if set -q HUED_FOREGROUND; and test -n "$HUED_FOREGROUND"
        set fg $HUED_FOREGROUND
    end

    _hued_apply_channel 11 111 "$bg"
    _hued_apply_channel 10 110 "$fg"
end
