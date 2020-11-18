pipeline {
  agent { label 'debian-buster' }
  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '10'))
  }

  stages {
    stage('Clean before launch'){
        steps{
            sh '''
            echo "clean"
            make clean
            rm -Rf ./build/
            '''
        }
    }
    stage('Setup RestructuredText'){
        steps {
            sh '''
            echo "Installing requirements"
            pip3 install -U pip setuptools
            pip3 install -r requirements.txt --upgrade
            '''
        }
    }
    stage('Gettext'){
        steps{
            sh '''
            echo "gettext and update po"
            make gettext
            sphinx-intl update -p build/locale/ -l fr
            make clean
            '''
        }
    }
    stage('Make HTML'){
        steps{
            sh '''
            make htmlen
            make -e SPHINXOPTS="-D language='fr'" htmlfr
            '''
        }
    }
    stage('Make EPUB'){
        steps{
            sh '''
            make epub_en
            make -e SPHINXOPTS="-D language='fr'" epub_fr
            '''
        }
    }
    stage('Make LatexPDF'){
        steps{
            sh '''
            echo "make latexpdf EN"
            make latexpdf_en  || true

            echo "make latexpdf FR"
            make -e SPHINXOPTS="-D language='fr'" latexpdf_fr || true
            '''
        }
    }
    stage('Copy static files'){
        steps{
            sh '''
            cp ./robots.txt build/en/doc
            cp ./robots.txt build/fr/doc
            mkdir ./build/en/doc/.well-known
            mkdir ./build/fr/doc/.well-known
            cp security.txt ./build/en/doc/.well-known
            cp security.txt ./build/en/doc/.well-known
            '''
        }
    }
    stage('Publish over SSH'){
        steps{
            sshPublisher alwaysPublishFromMaster: true,
                publishers: [sshPublisherDesc(configName: 'root@doc.ad.tranquil.it',
                transfers: [sshTransfer(excludes: '',
                    execCommand: '', execTimeout: 120000,
                    flatten: false,
                    makeEmptyDirs: false,
                    noDefaultExcludes: false,
                    patternSeparator: '[, ]+',
                    remoteDirectory: '/var/www/doc/wapt/en/doc/',
                    remoteDirectorySDF: false,
                    removePrefix: 'build/en/doc/',
                    sourceFiles: 'build/en/doc/**'),
                sshTransfer(excludes: '',
                    execCommand: '', execTimeout: 120000,
                    flatten: false,
                    makeEmptyDirs: false,
                    noDefaultExcludes: false,
                    patternSeparator: '[, ]+',
                    remoteDirectory: '/var/www/doc/wapt/fr/doc/',
                    remoteDirectorySDF: false,
                    removePrefix: 'build/fr/doc/',
                    sourceFiles: 'build/fr/doc/**'),
                sshTransfer(excludes: '',
                    execCommand: '', execTimeout: 120000,
                    flatten: false,
                    makeEmptyDirs: false,
                    noDefaultExcludes: false,
                    patternSeparator: '[, ]+',
                    remoteDirectory: '/var/www/doc/wapt/fr/doc/',
                    remoteDirectorySDF: false,
                    removePrefix: 'build/fr/epub/',
                    sourceFiles: 'build/fr/epub/*.epub'),
                sshTransfer(excludes: '',
                    execCommand: '', execTimeout: 120000,
                    flatten: false,
                    makeEmptyDirs: false,
                    noDefaultExcludes: false,
                    patternSeparator: '[, ]+',
                    remoteDirectory: '/var/www/doc/wapt/en/doc/',
                    remoteDirectorySDF: false,
                    removePrefix: 'build/en/epub/',
                    sourceFiles: 'build/en/epub/*.epub'),
                sshTransfer(excludes: '',
                    execCommand: '', execTimeout: 120000,
                    flatten: false,
                    makeEmptyDirs: false,
                    noDefaultExcludes: false,
                    patternSeparator: '[, ]+',
                    remoteDirectory: '/var/www/doc/wapt/fr/doc/',
                    remoteDirectorySDF: false,
                    removePrefix: 'build/fr/latex/',
                    sourceFiles: 'build/fr/latex/WAPT.pdf'),
                sshTransfer(excludes: '',
                    execCommand: '', execTimeout: 120000,
                    flatten: false,
                    makeEmptyDirs: false,
                    noDefaultExcludes: false,
                    patternSeparator: '[, ]+',
                    remoteDirectory: '/var/www/doc/wapt/en/doc/',
                    remoteDirectorySDF: false,
                    removePrefix: 'build/en/latex/',
                    sourceFiles: 'build/en/latex/WAPT.pdf')
                ],
                usePromotionTimestamp: false,
                useWorkspaceInPromotion: false,
                verbose: false)]
        }
    }
    stage('Clean release prod'){
            when {
                allOf  {
                        branch 'master'
                        tag "release-*"
                    }
            }
            steps {
                echo 'Cleanup prod'
                sshPublisher alwaysPublishFromMaster: true,
                publishers: [sshPublisherDesc(configName: 'root@wapt.fr',
                transfers: [sshTransfer(execCommand: 'rm -rf /var/www/wapt.fr/fr/doc-1.8/*'),
                sshTransfer(execCommand: 'rm -rf /var/www/wapt.fr/en/doc-1.8/*')],
                usePromotionTimestamp: false,
                useWorkspaceInPromotion: false,
                verbose: false)]
            }
    }
    stage('Publish release prod'){
            when {
                allOf  {
                        branch 'master'
                        tag "release-*"
                    }
            }
            steps {
                echo 'Publishing to doc.wapt.fr'
                sshPublisher alwaysPublishFromMaster: true,
                publishers: [sshPublisherDesc(configName: 'root@wapt.fr',
                transfers: [sshTransfer(excludes: '',
                    execCommand: '', execTimeout: 120000,
                    flatten: false,
                    makeEmptyDirs: false,
                    noDefaultExcludes: false,
                    patternSeparator: '[, ]+',
                    remoteDirectory: '/var/www/wapt.fr/en/doc-1.8/',
                    remoteDirectorySDF: false,
                    removePrefix: 'build/en/doc/',
                    sourceFiles: 'build/en/doc/**'),
                sshTransfer(excludes: '',
                    execCommand: '', execTimeout: 120000,
                    flatten: false,
                    makeEmptyDirs: false,
                    noDefaultExcludes: false,
                    patternSeparator: '[, ]+',
                    remoteDirectory: '/var/www/wapt.fr/fr/doc-1.8/',
                    remoteDirectorySDF: false,
                    removePrefix: 'build/fr/doc/',
                    sourceFiles: 'build/fr/doc/**'),
                sshTransfer(excludes: '',
                    execCommand: '', execTimeout: 120000,
                    flatten: false,
                    makeEmptyDirs: false,
                    noDefaultExcludes: false,
                    patternSeparator: '[, ]+',
                    remoteDirectory: '/var/www/wapt.fr/en/doc-1.8/',
                    remoteDirectorySDF: false,
                    removePrefix: 'build/en/latex/',
                    sourceFiles: 'build/en/latex/WAPT.pdf'),
                sshTransfer(excludes: '',
                    execCommand: '', execTimeout: 120000,
                    flatten: false,
                    makeEmptyDirs: false,
                    noDefaultExcludes: false,
                    patternSeparator: '[, ]+',
                    remoteDirectory: '/var/www/wapt.fr/fr/doc-1.8/',
                    remoteDirectorySDF: false,
                    removePrefix: 'build/fr/latex/',
                    sourceFiles: 'build/fr/latex/WAPT.pdf')
                ],
                usePromotionTimestamp: false,
                useWorkspaceInPromotion: false,
                verbose: false)]
            }
    }
  }

  post {
     success {
        rocketSend message: "Successful Build - ${env.JOB_NAME} ${env.BUILD_NUMBER} - ${env.BUILD_TIMESTAMP} (<${env.BUILD_URL}|Open>)",
        channel: 'documentation',
        rawMessage: true
    }

    failure {
        rocketSend message: "Build Failed - ${env.JOB_NAME} ${env.BUILD_NUMBER} - ${env.BUILD_TIMESTAMP} (<${env.BUILD_URL}|Open>)",
        channel: 'documentation',
        rawMessage: true
    }

    unstable {
        rocketSend message: "Unstable Build - ${env.JOB_NAME} ${env.BUILD_NUMBER} - ${env.BUILD_TIMESTAMP} (<${env.BUILD_URL}|Open>)",
        channel: 'documentation',
        rawMessage: true
    }

    aborted {
        rocketSend message: "Build Aborted - ${env.JOB_NAME} ${env.BUILD_NUMBER} - ${env.BUILD_TIMESTAMP} (<${env.BUILD_URL}|Open>)",
        channel: 'documentation',
        rawMessage: true
    }
    always {
        cleanWs()
    }
  }
 }
