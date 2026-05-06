# termcolor — set terminal background color based on nearest .termcolor file
#
# Place this file in ~/.config/fish/conf.d/

function _termcolor_apply --on-event fish_prompt
    set dir $PWD
    while test "$dir" != /
        if test -f "$dir/.termcolor"
            set hex (grep -m1 '^background=' "$dir/.termcolor" | cut -d= -f2 | string trim | string replace '#' '')
            if test -n "$hex"
                printf "\e]11;rgb:%s/%s/%s\a" \
                    (string sub -s 1 -l 2 $hex) \
                    (string sub -s 3 -l 2 $hex) \
                    (string sub -s 5 -l 2 $hex)
                return
            end
        end
        set dir (dirname $dir)
    end
    printf "\e]111;\a"
end
