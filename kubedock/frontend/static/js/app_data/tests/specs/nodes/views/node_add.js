/* eslint-env mocha */
/* eslint-disable no-unused-expressions */
mocha.allowUncaught();

import {expect, assert} from 'chai';
import sinon from 'sinon';
import {
  NodeAddStep as View,
  __RewireAPI__ as ViewRewireAPI
} from 'app_data/nodes/views';
import {rewired} from 'app_data/tests/test_utils';
import Model from 'app_data/model';

describe('nodes.views.NodeAddStep', function(){
    describe('validate', function(){
        let view, notify, utils, resetRewired,
            sandbox = sinon.sandbox.create(),
            setupInfo = { AWS : false, ZTF : false },
            symbols = [
                'hostname#',
                'hostn%ame',
                'hostna/me'
            ];

        view = new View({model: new Model.NodeModel(), setupInfo});
        view.ui = {
            'node_name' : {addClass:sandbox.stub().returns(true)},
            'block_device' : {addClass:sandbox.stub().returns(true)}
        };

        beforeEach(function(){
            [{utils}, resetRewired] = rewired(ViewRewireAPI, 'utils');
            notify = sandbox.stub(utils, 'notifyWindow');
        });

        afterEach(function () { sandbox.restore(); resetRewired(); });

        it('should return "false" if data is "undefined"', function() {
            expect(view.validate()).to.be.false;
        });

        it('should return "false" if hostname is empty', function() {
            expect(view.validate({hostname: ''})).to.be.false;
            assert(notify.calledWith('Hostname can\'t be empty'));
        });

        for (let symbol of symbols) {
            it(`should return "false" if hostname contain some special symbols "${symbol}"`,
            function() {
                expect(view.validate({hostname: symbol})).to.be.false;
                assert(notify.calledWith('Hostname can\'t contain some special symbols like ' +
                '"#", "%", "/" or start with "."'));
            });
        }

        it(`should return "false" if hostname start with symbols "."`, function() {
            expect(view.validate({hostname: '.'})).to.be.false;
            assert(notify.calledWith('Hostname can\'t contain some special symbols like ' +
            '"#", "%", "/" or start with "."'));
        });

        it(`should return "rtue" if hostname correct`, function() {
            expect(view.validate({hostname: 'example.ex.com'})).to.be.true;
        });

        it(`should return "false" if lsdevices is empty (ZFS)`, function() {
            expect(view.validate({hostname: 'example.ex.com', lsdevices: []})).to.be.false;
            assert(notify.calledWith('Block devices name can\'t be empty.'));
        });

        it(`should return "true" if hostname and lsdevices is correct (ZFS)`, function() {
            expect(view.validate({hostname: 'example.ex.uk', lsdevices: ['dev/sda2']})).to.be.true;
        });
    });

    describe('changeKubeType', function(){
        let view,
            sandbox = sinon.sandbox.create(),
            setupInfo = { AWS : false, ZTF : false };

        view = new View({model: new Model.NodeModel(), setupInfo });
        view.ui = { 'nodeTypeSelect' : {val:sandbox.stub().returns('2')} };

        afterEach(function () { sandbox.restore(); });

        it('"kube_type" should be equal undefined in model', function() {
            expect(view.model.get('kube_type')).to.be.undefined;
        });

        it('"kube_type" should be equal 2 in model', function() {
            view.changeKubeType();
            expect(view.model.get('kube_type')).to.be.equal(2);
        });
    });

    describe('changeHostname', function(){
        let view,
            sandbox = sinon.sandbox.create(),
            setupInfo = { AWS : false, ZTF : false };

        view = new View({model: new Model.NodeModel(), setupInfo });
        view.ui = { 'node_name' : {val:sandbox.stub().returns('new.example.com')} };

        afterEach(function () { sandbox.restore(); });

        it('"node_name" should be equal \' \' in model', function() {
            expect(view.model.get('hostname')).to.be.equal('');
        });

        it(`"node_name" should be equal ${view.ui.node_name.val()} in model`, function() {
            view.changeHostname();
            expect(view.model.get('hostname')).to.be.equal(view.ui.node_name.val());
        });
    });

    describe('complete', function(){
        let App, fakeNodes, view, resetRewired,
            sandbox = sinon.sandbox.create(),
            setupInfo = { AWS : false, ZTF : false };

        view = new View({model: new Model.NodeModel({}), setupInfo });
        view.ui = { 'node_name' : {val:sandbox.stub().returns('new.example.com'),
                                   addClass: sandbox.stub().returns(true) },
                    'nodeTypeSelect' : {val:sandbox.stub().returns('2')}
                };

        beforeEach(function(){
            [{App}, resetRewired] = rewired(ViewRewireAPI, 'App');
            fakeNodes = {fetch: sandbox.stub(), create: sandbox.stub()};
            sandbox.stub(App, 'getNodeCollection').returns($.Deferred().resolve(fakeNodes));
        });

        afterEach(function () { sandbox.restore(); resetRewired(); });

        it('should be called getNodeCollection', function() {
            view.changeKubeType();
            view.changeHostname();
            view.complete();
            expect(App.getNodeCollection).to.have.been.calledOnce;
        });
    });
});