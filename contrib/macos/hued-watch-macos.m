// hued-watch-macos: subscribe to macOS appearance changes and trigger
// `hued reapply` so OSC 10/11 colors are restored after the terminal resets
// them on light/dark switch.
//
// Build:  clang -framework Foundation -o hued-watch-macos hued-watch-macos.m
// Usage:  hued-watch-macos [path-to-hued]   (defaults to "hued" on $PATH)

#import <Foundation/Foundation.h>
#include <unistd.h>
#include <sys/wait.h>

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        const char *huedPath = (argc > 1) ? argv[1] : "hued";

        [[NSDistributedNotificationCenter defaultCenter]
            addObserverForName:@"AppleInterfaceThemeChangedNotification"
                        object:nil
                         queue:nil
                    usingBlock:^(NSNotification * _Nonnull note) {
            pid_t pid = fork();
            if (pid == 0) {
                execlp(huedPath, huedPath, "reapply", (char *)NULL);
                _exit(127);
            } else if (pid > 0) {
                int status;
                waitpid(pid, &status, 0);
            }
        }];

        [[NSRunLoop currentRunLoop] run];
    }
    return 0;
}
