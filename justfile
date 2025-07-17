default:
    echo "Available recipes: build, test, clean"

build:
    sudo rm -rf node_modules && .vscode/build.sh

test:
    scp "/Users/kurt/Developer/FG-plugins/Decky-Framegen/out/Decky-Framegen.zip" deck@192.168.0.6:~/Desktop

clean:
    rm -rf node_modules dist